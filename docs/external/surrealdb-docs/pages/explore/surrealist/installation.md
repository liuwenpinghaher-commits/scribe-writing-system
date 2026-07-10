---
title: "https://surrealdb.com/docs/explore/surrealist/installation"
url: "https://surrealdb.com/docs/explore/surrealist/installation"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/explore/surrealist/installation

Source: https://surrealdb.com/docs/explore/surrealist/installation

There are two primary ways to use Surrealist: as a desktop app or as a web app. While the desktop app offers more features and flexibility, the web app is more accessible and portable.  
This article will explain how to get up and running with both the desktop and web versions of Surrealist, and explains the key differences between the two.
##  Web app[](https://surrealdb.com/docs/explore/surrealist/installation#web-app)
The fastest way to get started with Surrealist is using the web app available at [app.surrealdb.com](https://app.surrealdb.com/). No additional installation is required, and you can start using Surrealist right away.
This web app contains most of the features available in the desktop app, but with a few limitations. For example, the web app may not be able to connect to insecure endpoints (non-HTTPS) due to browser restrictions.
Important
Due to security restrictions it will not always be possible to connect to databases hosted locally on localhost (or 127.0.0.1) using the web app in certain browsers.  
If you intend on doing so, we recommend using the desktop app instead as it does not have such restrictions.
##  Desktop app[](https://surrealdb.com/docs/explore/surrealist/installation#desktop-app)
The Surrealist Desktop app is the recommended way to use Surrealist, as it offers more features and flexibility compared to the web app. Some advantages of the desktop app include the ability to connect to insecure endpoints,  
directly opening `.surql` files from your file system, and more.
[Install Surrealist Desktop](https://surrealdb.com/surrealist?download)
###  Windows[](https://surrealdb.com/docs/explore/surrealist/installation#windows)
For Windows simply execute the downloaded installer and follow the instructions. Once installed, Surrealist will be ready to use.
###  macOS[](https://surrealdb.com/docs/explore/surrealist/installation#macos)
For macOS, download the .dmg file and drag the Surrealist icon to your Applications folder. The app will now be available in your Applications folder and can be opened from there.
###  Linux[](https://surrealdb.com/docs/explore/surrealist/installation#linux)
There are three ways to install Surrealist on Linux
  * •
`deb` for Ubuntu and Debian-based systems
  * •
`rpm` for Fedora and Red Hat-based systems
  * •
`AppImage` for other Linux distributions

Follow the instructions of your respective package manager to install Surrealist on your system.  
We currently do not plan on supporting other package formats, however the AppImage should work on most Linux distributions.
