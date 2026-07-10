---
title: "https://surrealdb.com/docs/explore/surrealist/faqs/faq-details"
url: "https://surrealdb.com/docs/explore/surrealist/faqs/faq-details"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/explore/surrealist/faqs/faq-details

Source: https://surrealdb.com/docs/explore/surrealist/faqs/faq-details

View some of the frequently asked questions regarding Surrealist. Questions which are frequently asked across our GitHub, Discord and other social platforms will be added here from time to time.
##  Which platforms does Surrealist support?[](https://surrealdb.com/docs/explore/surrealist/faqs/faq-details#which-platforms-does-surrealist-support)
Surrealist supports Windows, macOS, and Linux platforms. For Windows we provide an `exe` installer, macOS a `dmg` containing the executable, and for Linux we provide `deb`, `rpm`, and `AppImage` packages.  
In addition, we provide a universal web app which can be accessed from any platform with a modern web browser.
Any other distribution is unofficial and not supported by the Surrealist team.
##  Why does Surrealist not support version x.y.z?[](https://surrealdb.com/docs/explore/surrealist/faqs/faq-details#why-does-surrealist-not-support-version-xyz)
While we aim to keep Surrealist compatible with the latest stable release of SurrealDB, we do not guarantee compatibility with alpha and beta releases. Support for alpha and beta releases is added  
if we have the resources to do so, and often hidden behind a feature flag. If you are using an alpha or beta release of SurrealDB and are experiencing issues, please open an issue on our GitHub repository,  
as this gives us the opportunity to fix the issue before the stable release.
##  Which protocol should I use for my connections?[](https://surrealdb.com/docs/explore/surrealist/faqs/faq-details#which-protocol-should-i-use-for-my-connections)
This mostly depends on your preference and the database you are connecting to. The best overall protocol to use is `WSS` (Web Socket Secure) as it offers the best performance and security.  
However, this requires an SSL certificate to be configured on the remote database. If the remote has no SSL certificate, or you are connecting to localhost, you can use `WS` or `HTTP` which both work for unencrypted connections.
One thing to keep in mind is that unencrypted connections are not always available from the Web App and work better in the desktop app.
##  Why is Surrealist not connecting to my database?[](https://surrealdb.com/docs/explore/surrealist/faqs/faq-details#why-is-surrealist-not-connecting-to-my-database)
There may be reasons why Surrealist is unable to connect to a remote database. Some common reasons include specifying the wrong port, using the wrong protocol, or entering incorrect authentication details.
There may be more complex reasons such as network issues, firewalls, or the remote database not being available. You can always try connecting via the [CLI](https://surrealdb.com/docs/reference/cli/surrealdb-cli/overview) to see if the issue is with Surrealist or the remote database.
##  Could you add a feature to Surrealist?[](https://surrealdb.com/docs/explore/surrealist/faqs/faq-details#could-you-add-a-feature-to-surrealist)
We are always open to feature requests and suggestions. If you have a feature request, please open an issue on our [GitHub repository](https://github.com/surrealdb/surrealist).  
We will review the request and add it to our backlog if it aligns with our roadmap.
##  What is the license for Surrealist?[](https://surrealdb.com/docs/explore/surrealist/faqs/faq-details#what-is-the-license-for-surrealist)
Source code for Surrealist is licensed under MIT. You can find the license [here](https://github.com/surrealdb/surrealist/blob/main/LICENSE).  
Keep in mind that the SurrealDB database source code is not licensed under MIT.
