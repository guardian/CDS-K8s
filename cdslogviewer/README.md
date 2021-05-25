# cdslogviewer

## What is it?

cdslogviewer is a web-based user interface for viewing the logs output by cds_run.

cds_run captures the stdout and stderr from all of the methods it runs and outputs them to a text-based .log file
under the `/var/log/cds_backend/{routename}` directory.  Usually, the actual output from cds_run itself is not helpful
(unless you are developing cds_run itself).

While simple and convenient for the software, within a containerised environment it can be a bit tricky to actually
access and view these logs in a simple way.  Which is where this software comes along.

The `/var/log/cds_backend` directory within all the cds_run jobs should be provided by a shared persistent volume, e.g.
NFS.  This allows any number of cds_run pods to write to it while cdslogviewer is reading it.

cdslogviewer requires oauth2 bearer tokens to validate the user.  The easiest way to get these when developing is to run
from within a prexit-local setup deployed to a local minikube (see https://gitlab.com/codmill/customer-projects/guardian/prexit-local)

It is stateless and does not require any local storage beyond the shared logs volume, so can be scaled up and down
as you wish.

## Building and running locally

Unlike the other components in this repo, cdslogviewer does not need to interface with either RabbitMQ or Kubernetes.
You can therefore just build the frontend as per `Building and running in minikube` and then run `sbt run` (or run it in
Intellij or other editor).  You'll then access it through http://localhost:9000.

However, you'll still need to get hold of a bearer token in order to pass authentication.  You can do this by running
prexit-local and going to https://prexit.local and logging in.  Then, in your web browser, go to the Local Storage
(or Application) tab in the Developer Tools and look for "local storage".  Find the key called `pluto.access-key` and copy it.
This is your bearer token (aka JWT).  Then, in the browser console at http://localhost:9000 go to the same place, create
a new key called `pluto.access-key` and paste in the copied value.

The backend server will probably then complain that it has not got a public key to authenticate against.  You will have generated
the public key as part of the prexit-local setup; extract it from the prexit-local setup into the filesystem somewhere and
update `application.conf` to point to it.

Or just run it in minikube, which is what I do.


## Building and running in minikube

There is a suitable manifest for running a deployment of this at 
https://gitlab.com/codmill/customer-projects/guardian/prexit-local/-/blob/master/kube/cds/cds-logviewer.yaml.

This is a standard Scala/Play! framework backend with a React based frontend.

1. Build the frontend:
```bash
cd frontend/
yarn install
yarn dev  #this won't terminate, it watches the sources for updates
```

2. Build the backend and package the lot:
```bash
#make sure you are in the `cdslogviewer` dir and minikube is running
eval $(minikube docker-env)
sbt docker:publishLocal
```

3. Either deploy https://gitlab.com/codmill/customer-projects/guardian/prexit-local/-/blob/master/kube/cds/cds-logviewer.yaml,
   ensuring that `imagePullPolicy` is `Never` and the `image` ends in `:DEV`; or `kubectl get pods | grep logv` to find the 
   running pod and `kubectl delete pod {pod-name}` to delete it
   
## Testing

The simplest way to test is to find the running pod via `kubectl get pods | grep logv` and use `kubectl exec -it {pod-name} -- /bin/bash`
to access it.  Then, go to the configured filesystem path for logs and create a directory.  Hit F5 in the browser
view and you should see the directory appear in the tree on the left.  Create a text file and put some text in it,
refresh the browser again and navigate to the directory; you'll see the file. Click it to open and view.

If you add more text while the log is open you should see it automatically update every few seconds.