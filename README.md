# gcp-sql-export-poc
This a study case project to manage GCP resources using Terraform, populate a Cloud SQL database, then extract the data to Cloud Storage

## Requirements

1. [Install Docker](https://docs.docker.com/engine/install/)
2. [Install Terraform](https://developer.hashicorp.com/terraform/tutorials/gcp-get-started/install-cli)
3. [Install Google Cloud CLI](https://cloud.google.com/sdk/docs/install#windows)
   - After authenticate with `gcloud`, run the `gcloud auth configure-docker`


## Commands

Inside the repository folder run `terraform init` to initialize the Terraform project.
Then run the following commands to build and push the docker image to GCP.

```
$ docker build -t gcr.io/[PROJECT_ID]/[IMAGE_NAME]:[TAG] .
$ docker push gcr.io/[PROJECT_ID]/[IMAGE_NAME]:[TAG] .
```
