# cds-k8s

## What is it?


This is a framework which allows the Content Delivery System to run within a Kubernetes cluster.
It replaces the conventional watchfolder-trigger system and it manages the associated
Kubernetes resources.

The framework receives requests via RabbitMQ, provisions Kubernetes Jobs to run the CDS to fulfill the requests, monitors
the success/failure of the jobs and allows access to logs.

## Prerequisites

It's advisable to make sure you are familiar with the following concepts before diving into this repo:

- Kubernetes Pods, Jobs (run-to-completion), Configmaps and Persistent Volume Claims - see Google for these
- CDS Routes, Methods, Templates and Logs - https://github.com/guardian/content_delivery_system/
- RabbitMQ Exchanges, Queues and Subscriptions - https://www.rabbitmq.com/tutorials/tutorial-one-python.html

## What is the Content Delivery System?

The Content Delivery System can be found here - https://github.com/guardian/content_delivery_system/.  In a nutshell, 
it's a step-function runner which is designed to perform operations relating to media ingest and egest in a simple and
repeatable fashion.  For more information on CDS itself, consult the README file at the above URL.

## How does it work?

CDS lends itself to running in a Kubernetes environment as it is designed to be isolated and stateless as well as using
standard Unix concepts in operation.  We have also packaged it in Docker images for quite some time.

The CDS process itself is short-lived, needing to be triggered by something _external_ and given instructions on what
to do by specifying a route file and some initial metadata.  Previously this was carried out by a watchfolder system like
Watchman, but that function has been taken over by **cdsresponder**.  Instead of waiting for files to arrive in a directory,
this receives messages from a rabbitmq exchange and triggers based on those.

![System process diagram](system%20functions.png)

**cdsreaper** receives update messages from the k8s cluster and informs a rabbitmq exchange about them.  **cdsreaper**
then picks up and acts on these messages.  This split is made so that **cdsreaper** can remain a singleton, therefore
we don't need to worry about message de-duplication, but **cdsreaper** can be scaled up as necessary to process more at 
the same time.

CDS itself outputs log files into the filesystem, at `/var/log/cds_backend`.  This is substituted for a shared NFS mount via
a Persistent Volume Claim, which is also shared by the **cdslogviewer** app.
This is a standard Scala/Play! framework web app which offers a user interface to view the logs.  It's normally mounted
onto a URL at {pluto}/cds/.

## What are the components?

### cdsresponder

cdsresponder is the "active" part of the software.  It is designed to be scaled as necessary and it listens for messages
from rabbitmq and responds accordingly.  See the specific readme in the `cdsresponder/` directory for more details.

### cdsreaper

cdsreaper is designed as a singleton.  It maintains a "watch" on the Kubernetes jobs via the control plane, and receives
notifications when the state of jobs changes in its namespace.  When this happens, it notifies rabbitmq and then goes back
to listening again.  The rabbitmq message is picked up by cdsresponder which then handles the processing.

cdsreaper uses an external redis instance as a journal.  Each time a message is processed, a serial number provided by
Kubernetes is recorded.  The next time it starts up, cdsreaper tries to resume its watch from this number.  Therefore,
provided the outage time is less than the kubernetes event horizon no messages will get dropped even if cdsreaper has an outage.

### cdslogviewer

cdslogviewer is a user interface intended for viewing the logs.  It has no direct communication with the other components,
it simply lists out the log directories and yields the log contents for a viewer when asked.  See the specific readme in the
`cdslogviewer/` directory for more details.

## Setting up for Development

Since everything deploys via Docker images, you'll need a recent Docker version installed.

### Dev and automated tests
If you want to run the automated tests locally (_highly_ recommended, we don't like broken PRs!) then you'll need
a recent Python installed.  We develop against 3.8 normally.

As is standard with Python, create a virtualenv within which to work:

```bash
[repo-root] $ virtualenv -p /usr/local/bin/python3.8 venv/
[repo-root] $ source venv/bin/activate
[repo-root] (venv) $ pip install -r cdsresponder/requirements.txt
[repo-root] (venv) $ pip install -r reaper/requirements.txt
```

Since cdsresponder relies on lxml, you'll need a C compiler and the libxml2 development files installed.  See the
lxml documentation for more details.

To work in logviewer, you'll need Java 1.8+ (we use OpenJDK 11) and `sbt` the scala build tool.

### Running locally (minikube/prexit-local)
In order to run locally, you'll need a rabbitmq server to talk to and potentially pluto-deliverables to send messages in.
To run logviewer you'll also need an oauth2 IdP.
The simplest way to get these is to run minikube and to deploy prexit-local: https://gitlab.com/codmill/customer-projects/guardian/prexit-local.

Follow the setup instructions there, and you'll have an integrated environment with rabbitmq, oauth2 etc.

In the `kube/cds` directory of that repository you'll find deployments for all the components here, including all the
configmaps, storage configurations etc. required.  You can deploy them immediately, but they will probably get stuck
with `ErrImageNeverPull`.  This means that there is no docker image available yet and it's been told not to retrieve one
from the internet.  In order to build the images from the local source, you need to run:

```bash
$ eval $(minikube docker-env)
$ cd cdsresponder
$ docker build . -t guardianmultimedia/cdsresponder:DEV
$ cd ../cdsreaper
$ docker build . -t guardianmultimedia/cdsreaper:DEV
$ cd ../cdslogviewer
$ sbt docker:publishLocal
```

The first line evaluates a command from minikube, which points your local docker client to the docker daemon running
_in your minikube environment_.  This means that when you build the images "locally", they are actually going into your
container environment.

Once they are built, you should delete the existing running one with `kubectl delete {pod-name}` and wait for your newly
built version to start up.

If it is not running the right version, use `docker describe pod {podname} | grep image` to check that you are running
from the correct image name, and check that `eval $(minikube docker-env)` has been run _in your current session_ in order
to build the images on minikube not your local computer.

Rinse and repeat as you develop...

## Deploying for real

When making a real deployment, you actually have to provide the configuration elements that CDS itself expects as well
as deploying the framework here.  So here is a checklist for things that must be present in order for CDS to operate.

### Responder template

CDS is run as a job.  In order to configure this, cdsresponder expects a YAML template to be present at `cdsjob.yaml`.
An example is at https://gitlab.com/codmill/customer-projects/guardian/prexit-local/-/blob/master/kube/cds/responder-templates.yaml.
You can see that the Kubernetes job manifest is contained as a payload _within_ a ConfigMap.

This allows any arbitary configuration of the CDS job to be performed.  cdsresponder will override the "command" and
"labels" parameters but keep everything else the same.  For more details on the options available consult
https://kubernetes.io/docs/concepts/workloads/controllers/job/.

The prexit-local version of cdsjob.yaml has a bare minimum of required configuration.  The deployed one, which is kept
in the on-premesis secure deployment repo, is more comprehensive.

The responder template can be tested as follows:

- copy the contents of the `cdsjob.yaml` key into its own yaml file
- replace `command: ["/usr/local/bin/cds_run.pl"]` with `command: ["/bin/sleep","3600"]`
- submit to the cluster: `kubectl apply -f {yaml-file}.yaml`
- the job will now stay in a "running" state for 1 hour (3600 seconds).  In the meantime, you can find the pod that
is running via `kubectl get pods | grep cds-job` (it should be called `cds-job-template-{something}`) and enter into it
in order to inspect the environment: `kubectl exec -it {podname} -- /bin/bash`.
- make any changes, delete the job and re-submit it to check: `kubectl delete -f {yaml-file}.yaml; kubectl apply -f {yaml-file.yaml}`.
- etc. etc.

### Supplying the routes

CDS expects XML format route files to be present in the folder `/etc/cds_backend/routes`.  The simplest way to provide
this is to bundle the xml files up into a ConfigMap and mount it at this folder location.  

It's a pain to edit and verify xml when it is held within a yaml file though, so a script is provided called `generate-routes-config.py`.
This allows you to create a ConfigMap from a directory of files - similar to kubectl but a bit easier to use.
It _also_ has the option to validate and pretty-format the XML files before outputting them to the configmap, which
makes the final result a lot easier to read.  Run `./generate-routes-config.py --help` for more details (python 3.x required)

You need to make sure that the `metadata.name` field of the resulting config map matches the `volumes[].configMap.name`
parameter in the `cdsjob.yaml` file in order for the cluster to mount the routes in the right place.

### Supplying the templates

If you are performing metadata translations, you'll need templates to tell `metaxform` how to adapt the metadata.
These are normally present at `/etc/cds_backend/templates`.  Again this is best provided through a configmap, and again
`generate-routes-config.py` is the easiest way of generating this configmap.  This time though, don't use the xml validation/
pretty-print function unless _all_ of your templates are meant to be valid XML in their raw format.

Again, this configmap is provided to cdsrun through the `cdsjob.yaml` file.

### Supplying input metadata

Input metadata is extracted from a message queue and validated by cdsresponder.  However, cds_run expects to find a file
containing xml metadata in order to read it.  This can be present anywhere in the filesystem, and is indicated to cds_run
via the `--input-inmeta` commandline option when it is launched.  This option is supplied by cdsresponder when it over-writes
the template command (see `cdsresponder/cds/cds_launcher.py`).  cdsresponder will output a file to the location given by the
`INMETA_PATH` environment variable that is set in its container.

A shared persistent volume claim is the simplest way of enabling cdsresponder to write the file so cds_run can pick it up.
The PVC should be mounted at the same filesystem path in both the cds_run job container and the cdsresponder deployment container
so the paths are compatible.  NFS is a suitable storage medium choice for this; in prexit-local (minikube) a simple "localstorage"
provisioner is used.

### Temporary data paths

In addition, cds_run needs somewhere to store its in-progress datastore.  This is small and only needed for the life of the job,
so a memory-backed tmpfs mount is suitable.  This is expected to be present at `/var/spool/cds_backend`.
Some methods (e.g. image downloading/cropping) also require local scratch storage to be available.  In the "full" deployment
another tmpfs is present at `/scratch`

### Per-environment configuration

CDS supports per-environment configuration files which it expects to find in /etc/cds_backend/conf.d.  These are optional,
`key=value` format files whose contents can be accessed via the `{config:keyname}` substitution in a route file.
If you're using these, just like the templates and routes, they should be packaged into a configmap and mounted at /etc/cds_backend/conf.d.

### Accessing the logs

cds_run outputs logs to `/var/log/cds_backend/{routename}/{filename}.log`.  This should be another shared storage, e.g.
NFS (or local provisioner in minikube).  This storage should also be mounted by `cdslogviewer`, which offers auto-updating
viewing of the logs from the comfort of your web-browser

### Media

Finally, don't forget your media storage!  CDS will probably require at least read-only access to your storage in order
to locate the media and upload it.  SAN mounts are most easily propagated to the CDS job by having them mounted on the
kubernetes node itself and then using a `hostPath` mount to make them visible to the container

