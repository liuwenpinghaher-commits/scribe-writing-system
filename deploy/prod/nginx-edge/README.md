# 边缘 nginx（主机 `/opt/nginx-docker`）

- 公网主域：`tonglu.example.com`（铜炉 / scribe3）
- 旧域 `www.example.com` / `example.com` → 301 至主域
- 专访：`zhuanfang.example.com`
- TLS：`tonglu` 为 Let's Encrypt；续期后 deploy hook 复制到 `ssl/` 并 reload

本目录为参考配置；线上真源在 demo 机 `/opt/nginx-docker/conf/nginx.conf`。
修改 bind-mount 的单文件时，须 **tee 覆写同 inode** 或 **重建容器**，勿 `cp` 换 inode。
