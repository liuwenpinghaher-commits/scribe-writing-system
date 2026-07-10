---
title: "https://surrealdb.com/docs/manage/cloud/network-access"
url: "https://surrealdb.com/docs/manage/cloud/network-access"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/manage/cloud/network-access

Source: https://surrealdb.com/docs/manage/cloud/network-access

How you expose and reach SurrealDB Cloud affects **security** , **latency** , and **compliance**. Cloud supports several patterns; pick the one that matches your threat model and cloud architecture.
##  IP allowlisting[](https://surrealdb.com/docs/manage/cloud/network-access#ip-allowlisting)
Restrict which **client IP addresses or CIDR ranges** may connect to your instance’s public endpoint. This reduces exposure to the open internet and is a common baseline for admin APIs and application tiers with fixed egress IPs.
##  VPC peering and private connectivity[](https://surrealdb.com/docs/manage/cloud/network-access#vpc-peering-and-private-connectivity)
Where available, connect your cloud **VPC** to SurrealDB Cloud so traffic stays on provider networks instead of the public internet. Options and onboarding vary by region and plan—confirm with your account team if you need private routing between application subnets and the database.
##  AWS PrivateLink[](https://surrealdb.com/docs/manage/cloud/network-access#aws-privatelink)
**AWS PrivateLink** offers interface endpoints so traffic between your VPC and SurrealDB Cloud does not traverse the public internet. Enterprise setups often require coordinated enablement and DNS configuration.
![](https://surrealdb.com/docs/manage/cloud/~/assets/img/image/cloud/aws-privatelink-surrealist-light.png)![](https://surrealdb.com/docs/manage/cloud/~/assets/img/image/cloud/aws-privatelink-surrealist-light.png)
##  Detailed configuration[](https://surrealdb.com/docs/manage/cloud/network-access#detailed-configuration)
Instance-level rules (including outbound HTTP access from queries) and console steps are documented here: **[Network access](https://surrealdb.com/docs/build/deployment/surrealdb-cloud/operations/network-access)**.
