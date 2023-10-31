<div align="center" markdown>
<img src="https://github-production-user-asset-6210df.s3.amazonaws.com/118521851/279370909-385503d2-81be-4e46-8fe6-62f91c14269a.png"/>

# Convert and copy multiple CVAT projects into Supervisely at once

<p align="center">
  <a href="#Overview">Overview</a> •
  <a href="#Preparation">Preparation</a> •
  <a href="#How-To-Run">How To Run</a>
</p>

[![](https://img.shields.io/badge/supervisely-ecosystem-brightgreen)](https://ecosystem.supervise.ly/apps/supervisely-ecosystem/cvat-to-sly/migration_tool)
[![](https://img.shields.io/badge/slack-chat-green.svg?logo=slack)](https://supervise.ly/slack)
![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/supervisely-ecosystem/cvat-to-sly)
[![views](https://app.supervise.ly/img/badges/views/supervisely-ecosystem/cvat-to-sly/migration_tool.png)](https://supervise.ly)
[![runs](https://app.supervise.ly/img/badges/runs/supervisely-ecosystem/cvat-to-sly/migration_tool.png)](https://supervise.ly)

</div>

## Overview

This application allows you to copy multiple projects from CVAT instance to Supervisely instance, you can select which projects should be copied, labels and tags will be converted automatically. You can preview the results in the table, which will show URLs to corresdponding projects in CVAT and Supervisely.<br>

\*️⃣ If you want to upload data, which was already exported from CVAT instance, you can use this [Import CVAT](https://ecosystem.supervisely.com/apps/cvat-to-sly/import_cvat) app from Supervisely Ecosystem.<br>

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

![credentials](https://github-production-user-asset-6210df.s3.amazonaws.com/118521851/271299369-5c1c3610-bd10-4644-a345-3d0b5557e13a.png)

If everything was done correctly, you will see the following message in the app UI:

- ✅ Successfully connected to `http://192.168.1.100:8080` as `admin`.<br>

NOTE: The app will not save your credentials, you will need to enter them every time you launch the app. To save your time you can use the team files to store your credentials.

## How To Run

NOTE: In this section, we consider that you have already connected to CVAT and instance and have the necessary permissions to work with them. If you haven't done it yet, please refer to the [Preparation](#Preparation) section.<br>
So, here is the step-by-step guide on how to use the app:

**Step 1:** Select projects to copy<br>
After connecting to the CVAT instance, list of the projects will be loaded into the widget automatically. You can select which projects you want to copy to Supervisely and then press the `Select projects` button.<br>

![select_projects](https://github-production-user-asset-6210df.s3.amazonaws.com/118521851/271299390-cfada065-8afd-4a9c-bf4c-4040925cc2b6.png)

**Step 2:** Take a look on list of projects<br>
After completing the `Step 1️⃣`, the application will retrieve information about the projects from CVAT API and show it in the table. Here you can find the links to the projects in CVAT, and after copying the projects to Supervisely, links to the projects in Supervisely will be added to the table too.<br>

![projects_table](https://github-production-user-asset-6210df.s3.amazonaws.com/118521851/271299395-180e1e41-d9f8-46bf-aac5-1caf349b9699.png)<br>

**Step 3:** Press the `Copy` button<br>
Now you only need to press the `Copy` button and wait until the copying process is finished. You will see the statuses of the copying process for each project in the table. If any errors occur during the copying process, you will see the error status in the table. When the porcess is finished, you will see the total number of successfully copied projects and the total number of projects that failed to copy.<br>

ℹ️ CVAT projects can contain both images and videos, but Supervisely project can contain only one type of data. If the CVAT project contains both images and videos, the application will create two projects in Supervisely: one with images and one with videos and you will find two links to the Supervisely projects in the table.<br>

ℹ️ Currently conversion of Cuboid geometry is not supported, corresponding annotations will be skipped.<br>
ℹ️ Supervisely doesn't support Ellipse geometry, this kind of labels will be skipped.<br>

![copy_projects](https://github-production-user-asset-6210df.s3.amazonaws.com/118521851/271299400-bf33a936-49d6-4ee3-bb1c-2ab4955997ac.png)<br>

![finished](https://github-production-user-asset-6210df.s3.amazonaws.com/118521851/271299408-807acfbf-87ed-45cf-8c82-3ab2d4bab09c.png)<br>

The application will be stopped automatically after the copying process is finished.<br>

## Acknowledgement

- [CVAT github](https://github.com/opencv/cvat) ![GitHub Org's stars](https://img.shields.io/github/stars/opencv/cvat?style=social)
- [CVAT documentation](https://opencv.github.io/cvat/docs/)
