<div align="center" markdown>
<img src="https://github-production-user-asset-6210df.s3.amazonaws.com/118521851/281444746-cf7e34e0-6fd6-4ffb-9db0-50c4d8170fe9.png"/>

# Convert and copy multiple CVAT projects into Supervisely at once

<p align="center">
  <a href="#Overview">Overview</a> •
  <a href="#Preparation">Preparation</a> •
  <a href="#How-To-Run">How To Run</a>
</p>

[![](https://img.shields.io/badge/supervisely-ecosystem-brightgreen)](../../../../supervisely-ecosystem/cvat-to-sly/import_cvat)
[![](https://img.shields.io/badge/slack-chat-green.svg?logo=slack)](https://supervisely.com/slack)
![GitHub release (latest SemVer)](https://img.shields.io/github/v/release/supervisely-ecosystem/cvat-to-sly)
[![views](https://app.supervisely.com/img/badges/views/supervisely-ecosystem/cvat-to-sly/import_cvat.png)](https://supervisely.com)
[![runs](https://app.supervisely.com/img/badges/runs/supervisely-ecosystem/cvat-to-sly/import_cvat.png)](https://supervisely.com)

</div>

## Overview

This application allows you convert images and videos with annotations from CVAT format to Supervisely format for multiple projects at once using archive or folder with projects in CVAT format (`CVAT for images 1.1` both for images and videos).<br>

\*️⃣ If you want to copy projects directly from CVAT instance you can use fully automated [CVAT to Supervisely Migration Tool](../../../../supervisely-ecosystem/cvat-to-sly/migration_tool) app from Supervisely Ecosystem.<br>

## Preparation

First, you need to export your data from CVAT referreing to [this guide](https://opencv.github.io/cvat/docs/getting_started/#export-dataset). Make sure that you have selected `CVAT for images 1.1` format for both images and videos, while exporting. Learn more about CVAt format in [official documentation](https://opencv.github.io/cvat/docs/manual/advanced/formats/format-cvat/#cvat-for-videos-export).<br>

You can download an example of data for import [here](https://github.com/supervisely-ecosystem/cvat-to-sly/files/12782004/cvat_examples.zip).<br>
After exporting, ensure that you have the following structure of your data for running this app:

```text
📦 folder-with-projects
 ┣ 📂 project-with-images
 ┃ ┗ 📂 task-with-images
 ┃ ┃ ┣ 📂 images
 ┃ ┃ ┃ ┣ 🏞️ car_001.jpeg
 ┃ ┃ ┃ ┣ 🏞️ car_002.jpeg
 ┃ ┃ ┃ ┗ 🏞️ car_003.jpeg
 ┃ ┃ ┗ 📄 annotations.xml
 ┣ 📂 project-with-videos
 ┃ ┣ 📂 task-with videos
 ┃ ┃ ┣ 📂 images
 ┃ ┃ ┃ ┣ 🏞️ frame_000000.PNG
 ┃ ┃ ┃ ┣ 🏞️ frame_000001.PNG
 ┃ ┃ ┃ ┣ 🏞️ frame_000002.PNG
 ┃ ┃ ┃ ┣ 🏞️ frame_000003.PNG
 ┃ ┃ ┃ ┣ 🏞️ frame_000004.PNG
 ┃ ┃ ┃ ┣ 🏞️ frame_000005.PNG
 ┃ ┃ ┃ ┣ 🏞️ frame_000006.PNG
 ┃ ┃ ┃ ┣ 🏞️ frame_000007.PNG
 ┃ ┃ ┃ ┣ 🏞️ frame_000008.PNG
 ┃ ┃ ┃ ┣ 🏞️ frame_000009.PNG
 ┃ ┃ ┃ ┣ 🏞️ frame_000010.PNG
 ┃ ┃ ┗ 📄 annotations.xml
```

In output of this app you will receive the following structure on Supervisely platform:

```text
Project with images in Supervisely, containing one dataset with images and annotations:
📂 project-with-images
┗ 📂 task-with-images
  ┣ 🏞️ car_001.jpeg
  ┣ 🏞️ car_002.jpeg
  ┗ 🏞️ car_003.jpeg

and project with videos in Supervisely, containing one dataset with images and annotations:
📂 project-with-videos
┗ 📂 task-with-videos
  ┗ 🎬 video_file.mp4 (The name for video will be extracted from CVAT annotation, same as on CVAT instance)

```

ℹ️ CVAT projects can contain both images and videos, but Supervisely project can contain only one type of data. If the CVAT project contains both images and videos, the application will create two projects in Supervisely: one with images and one with videos.<br>

## How To Run

### Uploading an archive with projects in CVAT format

**Step 1:** Run the app<br>

<img src="https://github-production-user-asset-6210df.s3.amazonaws.com/118521851/271954839-e180b28e-def0-4e74-943b-2f65e0f229a9.png"/><br>

**Step 2:** Drag and drop the archive or select it in Team Files<br>

<img src="https://github-production-user-asset-6210df.s3.amazonaws.com/118521851/271954855-5ac6809d-6663-44cb-b027-8c2ea26d8303.png"/><br>

**Step 3:** Press the `Run` button<br>

### Uploading a folder with projects in CVAT format

**Step 1:** Run the app<br>

**Step 2:** Drag and drop the folder or select it in Team Files<br>

<img src="https://github-production-user-asset-6210df.s3.amazonaws.com/118521851/271954859-b0455c99-c59c-481b-8793-caf02f308a64.png"/><br>

**Step 3:** Press the `Run` button<br>

After completing the `Step 3️⃣`, the application will start converting and copying your projects to Supervisely, after completing the process the application will automatically stops.<br>

ℹ️ Currently conversion of Cuboid geometry is not supported, corresponding annotations will be skipped.<br>
ℹ️ Supervisely doesn't support Ellipse geometry, this kind of labels will be skipped.<br>

## Acknowledgement

- [CVAT github](https://github.com/opencv/cvat) ![GitHub Org's stars](https://img.shields.io/github/stars/opencv/cvat?style=social)
- [CVAT documentation](https://opencv.github.io/cvat/docs/)
