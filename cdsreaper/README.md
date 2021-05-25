# cdsreaper

## What is it, and how does it work?

As per the root readme, the job of cdsreaper is to listen to messages from the Kubernetes control plane indicating when
jobs have started, stopped or finished and to inform the other components of this through rabbitmq.

cdsreaper is intended as a singleton - i.e. never more than one copy running in a cluster.  This means that we don't
have to worry about complex locking mechanisms and we can rely on Kubernetes itself to restart us on failure.

It's also _not_ intended to do any processing itself.  This keeps the code much simpler and cleaner, and therefore
more reliable.  It means that we should not suffer and performance loss from the singleton restriction.

In order to actually _perform_ the "reaping" tasks - downloading and stdout logs from the pod, deleting the completed job,
etc. **cdsresponder** receives messages from cdsreaper and then acts on them.  This is generally a higher-performance
way of managing the process because cdsresponder can have many instances with rabbitmq handling up the division of work
between them.  If any of these fail for any reason, it won't affect cdsreaper.

## Why does it require redis?  Journalling.

All of the safety and simplicity designed in can't protect us against hardware failure, cluster resource starvation, etc.
It's therefore assumed when starting up that there _may_ have been events in the past that we have not dealt with yet.

With each event notification sent, Kubernetes sends us a kind of "serial number".  When setting up the watcher, we can
tell it to resume from a given serial number, providing it is not _so_ long ago that Kubernetes has forgotten about it.

Whenever we finish processing a notification (i.e. rabbitmq has sent _back_ a delivery confirmation, so we know it is on 
a queue) we store this serial number in a redis key.  At startup, we request Kubernetes to start streaming us events
_from this serial number_.  Provided that Kubernetes remembers this far back, we will then be sent any messages that happened
in the absence of the process running.  If we are already over the horizon, and Kubernetes has no memory of the serial number,
then a warning is logged out and we start again from the most recent event.

## More event safety

The job of cdsreaper is done _once rabbitmq confirms receipt of the message_.  After this, it's up to cdsresponder and
rabbitmq to ensure that the message gets processed.  This is done using "consumer acknowledgements".

cdsresponder sets up a queue to listen to the exchange we are publishing to and attaches to it.  The queue is configured
_not_ to delete a message until it gets confirmation from the consumer (cdsresponder) that the message has been processed
correctly.  Absent of this confirmation, the message will get re-delivered.  cdsreaper does not need to be concerned with
any of these mechanics as it's taken care of by rabbitmq.

## Why do we need to know about job events?

Kubernetes jobs are not deleted automatically, unless they were started by a cronjob.  Therefore, without some kind of a
reaping process completed jobs will grow forever, cluttering up the cluster databases and reducing performance.  Once a job
completes, we need to make sure it's removed; but we should make sure we have saved whatever we need from its metadata and
logs first.

Furthermore, it is convenient to have a "hook" mechanism for triggering any other workflows that need to know about job
start and finish.  For example, we can now set a "pending" field in pluto-deliverables based on receipt of the cdsresponder
message that confirms _creation_ of the job and "running" when the job activates (if we have to pull the cds-backend image
it can take 60 seconds or more).

## Message formats

cdsresponder does not respond to any incoming rabbitmq messages.  It subscribes (via the Kubernetes API) to all job
events from the namespace within which it was started up.

cdsreaper outputs to the **cdsresponder** rabbitmq exchange.  This is a "topic" exchange, where every message requires a
routing key that can be used for selective subscription.

We output messages with the following routing keys:

- `cds.job.running`
   A container entered the running state _for the first time_
- `cds.job.retry`
   A container entered the running state but not for the first time - this means that the last one failed.
- `cds.job.starting`
   A new job was created and is in the process of being set up. Nothing is running until the `cds.job.running` message is output.
- `cds.job.failed`
   A job has failed, i.e. it has reached the maximum number of retries and none of the containers succeeded
- `cds.job.success`
   A job has completed, i.e. one of the containers has reported success
  
Messages contain the following payload fields, in json format:

- `job-id` (string)
   Cluster-provided UUID of the job object
- `job-name` (string)
  Cluster-provided name of the job affected
- `job-namespace` (string)
  Namespace within which the job exists
- `retry-count` (int)
  Number of retries which have been attempted. 0 if it's the first attempt.
- `failure-reason` (string, ONLY for `cds.job.failed`)
  Reason given by the cluster that the job failed.
  
A recipient can look up content from the cluster by calling the Kubernetes API with the `job-name` and `job-namespace`
parameters, since we don't delete or otherwise affect the job here.  **However** the intended consumer is cdsresponder,
which **does** delete the job upon receipt of `cds.job.failed` or `cds.job.success`.  Be warned.

## Running and testing

cdsreaper should be run as a Deployment in a Kubernetes cluster with a replica count of 1.  If the replica count is
higher you will get multiple messages of the types above output (one per running instance).

It needs no storage of its own, but it does expect to find a redis instance within which it can maintain its event
journal.  It also expects to find a rabbitmq instance to send events to.

All configuration is carried out via environment variables.  Grep the source for `os.environ` to see what is expected
and why.  A complete sample configuration can be found in https://gitlab.com/codmill/customer-projects/guardian/prexit-local/-/tree/master/kube/cds.
(specifically `cds-reaper.yaml`, `cds-redis.yaml`)

It also **needs a service account** to be set up which gives it permission to Read and Watch job events from the cluster.
Consult the sample configuration at https://gitlab.com/codmill/customer-projects/guardian/prexit-local/-/blob/master/kube/cds/cds-roles.yaml
for details.

The simplest way to test the system is to deploy pluto-local to a local minikube cluster (see the instructions at
https://gitlab.com/codmill/customer-projects/guardian/prexit-local) and make sure that the manifests at `cds/` are deployed.
They _should_ refer to local images with a `:DEV` suffix, which you'll have to build yourself:

```
$ source venv/bin/activate
(venv) $ cd cdsreaper
(venv) $ eval $(minikube docker-env)
(venv) $ docker build . -t guardianmultimedia/cds-reaper:DEV
```

This is in-line with the other prexit components.
