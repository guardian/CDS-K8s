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