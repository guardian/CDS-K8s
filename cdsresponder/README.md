# cdsresponder

## What is it?

cdsresponder is the "active" portion of this software.  Its job is to listen for relevent events from rabbitmq and to
trigger processes in response to them.

The main `cdsresponder` script contains an object called `Command` and simply calls a method on it when the program is run.
This is because it has been taken almost verbatim from the pluto-deliverables codebase, which is Django-based.

It reads the `rabbitmq/mappings.py` file, which associates the name of an exchange to listen to with an instance of a
subclass of the `MessageProcessor` class.

The `MessageProcessor` class contains the generic receiving logic, ensuring that the json schema of the message is valid
and that processing exceptions are caught.  The subclasses of `MessageProcessor` provide the actual processing logic for
the message type.   Consult the in-code comments in `MessageProcessor` for details on how this operates.

There are two seperate processes coded into the software, in `rabbitmq/UploadRequestedProcessor`
and `rabbitmq/K8MessageProcessor`.

### UploadRequestedProcessor

This listens to the `pluto-deliverables` exchange (name is hard-coded in `rabbitmq/mappings.py`) for messages matching
`deliverables.syndication.*.upload` (remember in rabbitmq, `*` means "any word without . character" and `#` means "anything at all").
It's expected that the routing key is of the form `deliverables.syndication.{platform-name}.upload`.

The expected schema is defined at the top of `UploadRequestProcessor` - the only required parameters are `routename` (the
name of the CDS route to trigger) and `inmeta` (raw xml content of the inmeta data).

The content of `inmeta` is then verified to ensure that it matches the schema defined in `inmeta.xsd`.  See the CDS
software repo at https://github.com/guardian/content_delivery_system/ for more details on this specific format.

If the content is not valid then a message is pushed to the `cdsresponder` exchange (defined as `my_exchage` at the top
of UploadRequestedProcessor) with the routing key `cds.job.invalid`.  The json body of this message is the same as the
incoming job request but with an additional string field `error` which is a descriptive string as to how the xml
failed validation.

The software expects to find a Kubernetes Job manifest called `cdsjob.yaml` at either the path location in the environment
variable `TEMPLATES_PATH`, the `cdsresponder` source directory or in `/etc/cdsresponder/templates/`.  The software will
fail if it can't be found in any location.

This yaml file will be parsed as a job manifest, and then the `Command` and `labels` sections over-written with relevant data
for this job.  The job is then submitted to the K8s cluster and a `cds.job.started` message is output to the `cdsresponder`
exchange.

At this point processing ends - further actions are taken when we receive a job succeeded/failed message from cdsreaper.

### K8MessageProcessor

This listens to the `cdsresponder` exchange for messages matching `cds.job.*`.  When it receives a `success` or `failed`
message, it downloads the contents of the pod's stdout log to a text file in the path given by the environment variable
`POD_LOGS_BASEPATH` - if this is not set then no logs are saved.

It then deletes the job, which will delete the associated pod and container resources from the cluster.

### Kubernetes permissions

In order to perform these operations, cdsresponder must be run under a service account that has permissions to create,
read, list and delete jobs.  It also needs to be able to read and list pods, in order to be able to get hold of the logs.

The sample deployment at https://gitlab.com/codmill/customer-projects/guardian/prexit-local/-/blob/master/kube/cds/cds-roles.yaml
shows a suitable role configuration.  See https://kubernetes.io/docs/reference/access-authn-authz/rbac/ for more details
about how access permissions work in Kubernetes.

## Event safety

The broker queues are configured to require consumer acknowledgement.  This acknowledgement is given only when processing
is completed - if it worked without error, or there is an unrecoverable error, the message is "acked" and removed from the queue.
If there was a recoverable error, then it is "nacked" with a request to requeue the message.  It should then get tried again.

## Running and testing

It's possible to run the software on your local machine outside a cluster, but then you need to configure external access
permissions to Kubernetes as well as providing a rabbitmq cluster to talk to.  The simplest way to test it is to build the
image and run it in prexit-local - follow the instructions in the root readme.

Once you have the pods running, in order to test things are working, set up two terminal windows to tail the logs from
cds-responder and cds-reaper respectively (`kubectl logs -f deployment/cds-responder`).  Once you can see that they are
running properly, go to https://prexit.local/rabbitmqadmin in your browser and log in with the username/password `pluto-ng`
(or whatever you set them to, if you changed them).

Go to the `Exchanges` tab.
You should see a "pluto-deliverables" exchange and a "cdsresponder" exchange.  Go to the "pluto-deliverables" exchange
and send a message.  For the content body, use the contents of the `testmsg.txt` file in the root of this repo, and for the
routing key use `deliverables.syndication.test.upload`.

Once you send the message, you should see cdsresponder take it and validate the message.  It will then create a job which you
can see via `kubectl get jobs` in another terminal.

Once the job is created, you should see cdsreaper register this fact, and an acknowledgement from cdsresponder.

The job should retry once or twice before failing (you don't have any routes set up) and you'll see the `retry` and `failed`
messages being relayed from cdsreaper to cdsresponder.  cdsresponder should then delete the job.