<div align="center" markdown>
<img src="https://github-production-user-asset-6210df.s3.amazonaws.com/118521851/271228440-cde1aca9-b535-42ae-b1db-e277b626d128.png"/>

# Placeholder for app short description

<p align="center">
  <a href="#Overview">Overview</a> •
  <a href="#Preparation">Preparation</a> •
  <a href="#How-To-Run">How To Run</a>
</p>

[![](https://img.shields.io/badge/supervisely-ecosystem-brightgreen)](https://ecosystem.supervise.ly/apps/supervisely-ecosystem/cvat-to-sly/migration_tool)
[![](https://img.shields.io/badge/slack-chat-green.svg?logo=slack)](https://supervise.ly/slack)
![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/supervisely-ecosystem/cvat-to-sly/migration_tool)
[![views](https://app.supervise.ly/img/badges/views/supervisely-ecosystem/cvat-to-sly_migration_tool.png)](https://supervise.ly)
[![runs](https://app.supervise.ly/img/badges/runs/supervisely-ecosystem/cvat-to-sly_migration_tool.png)](https://supervise.ly)

</div>

## Overview

ℹ️ Currently conversion of Cuboid geometry is not supported, corresponding annotations will be skipped.<br>
ℹ️ Supervisely doesn't support Ellipse geometry, this kind of labels will be skipped.<br>

This application allows you to transfer multiple projects from CVAT instance to Supervisely instance, you can select which projects should be transferred, labels and tags will be converted automatically. You can preview the results in the table, which will show URLs to corresdponding projects in CVAT and Supervisely.<br>

## Preparation

In order to run the app, you need to obtain credentials to work with CVAT API. You will need the following information:

- CVAT server URL (e.g. `http://192.168.1.100:8080`)
- CVAT username (e.g. `admin`)
- CVAT password (e.g. `qwerty123`)

You can use the address from the browser and your credentials to login to CVAT (you don't need any API specific credentials).<br>
Now you have two options to use your credentials: you can use team files to store an .env file with or you can enter the credentials directly in the app GUI. Using team files is recommended as it is more convenient and faster, but you can choose the option that is more suitable for you.

### Using team files

You can download an example of the .env file [here](https://github.com/supervisely-ecosystem/cvat-to-sly/files/12748716/cvat.env.zip) and edit it without any additional software in any text editor.<br>
NOTE: you need to unzip the file before using it.<br>

1. Create a .env file with the following content:
   `CVAT_SERVER_ADDRESS="http://192.168.1.100:8080"`
   `CVAT_USERNAME="admin"`
   `CVAT_PASSWORD="qwerty123"`
2. Upload the .env file to the team files.
3. Right-click on the .env file, select `Run app` and choose the `CVAT to Supervisely Migration Tool` app.

The app will be launched with the credentials from the .env file and you won't need to enter it manually.
If everything was done correctly, you will see the following message in the app UI:

- ℹ️ Connection settings was loaded from .env file.
- ✅ Successfully connected to `http://192.168.1.100:8080` as `admin`.

### Entering credentials manually

1. Launch the app from the Ecosystem.
2. Enter the CVAT server URL, username and password in the corresponding fields.
3. Press the `Connect to CVAT` button.

If everything was done correctly, you will see the following message in the app UI:

- ✅ Successfully connected to `http://192.168.1.100:8080` as `admin`.<br>

NOTE: The app will not save your credentials, you will need to enter them every time you launch the app. To save your time you can use the team files to store your credentials.

## How To Run

Section for the app running. Describe how to run the app step by step.

**Step 1:** Describe actions in step.<br><br>

**Step 2:** Describe actions in step.<br><br>
<img src="placeholder for screenshot"/><br><br>

After finishing using the app, don't forget to stop the app session manually in the App Sessions. The app will write information about the text prompt and CLIP score to the image metadata. You can find this information in the Image Properties - Info section of the image in the labeling tool.
