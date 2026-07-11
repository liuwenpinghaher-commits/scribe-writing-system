---
title: "https://surrealdb.com/docs/manage/cloud/organisations-and-users"
url: "https://surrealdb.com/docs/manage/cloud/organisations-and-users"
source: "SurrealDB Docs"
crawled_at: "2026-07-09T15:29:02.180962+00:00"
---

# https://surrealdb.com/docs/manage/cloud/organisations-and-users

Source: https://surrealdb.com/docs/manage/cloud/organisations-and-users

SurrealDB Cloud is organised around **organisations** —billing, instances, and policies typically belong to an organisation, and users are invited to collaborate with appropriate **roles**.
##  Organisations[](https://surrealdb.com/docs/manage/cloud/organisations-and-users#organisations)
Create an **organisation** for each company, department, or environment you want to isolate (for example, production versus development). Organisation boundaries help separate **invoices** , **instances** , and **access** so one team cannot accidentally change another’s resources.
##  Inviting team members[](https://surrealdb.com/docs/manage/cloud/organisations-and-users#inviting-team-members)
**Invite** colleagues by email from the organisation settings. Invitations should go to named accounts; avoid shared mailboxes for administrative roles. Remove or rotate access when people leave the project.
##  Roles and access control[](https://surrealdb.com/docs/manage/cloud/organisations-and-users#roles-and-access-control)
**Role-based access control (RBAC)** limits what each member can do: for example, billing administration versus instance creation versus read-only monitoring. Assign the **least privilege** role that still lets someone do their job, and use separate organisations if you need hard isolation between tenants.
Audit who can create instances, change network rules, and manage backups or restores periodically—those actions carry the highest risk.
