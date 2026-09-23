# 文档目录

本目录面向第一次接触 Docker、Kubernetes、GitHub Actions 和 Argo CD 的使用者。

阅读顺序：

1. [01-使用文档.md](01-使用文档.md)：启动环境、访问系统、发布新版本、查看日志、回滚。
2. [04-一次发布到底发生了什么.md](04-一次发布到底发生了什么.md)：用流程图和真实提交，逐站说明 GitHub Actions 如何推送 GHCR 镜像，以及怎样验证部署。
3. [03-ArgoCD使用文档.md](03-ArgoCD使用文档.md)：第一次安装 Argo CD、注册应用、登录界面和排查同步问题。
4. [02-GitHub配置详解.md](02-GitHub配置详解.md)：GitHub 仓库、Actions、GHCR、Kubernetes 和 Argo CD 每个配置的解释。

项目地址：

~~~text
https://github.com/zsong0348-pixel/hello-k8s-cicd
~~~

先记住三条：

1. 改代码后提交 Git，GitHub Actions 自动测试和构建镜像。
2. Git 中的 k8s/deployment.yaml 决定 Kubernetes 应运行哪个版本。
3. 正常发布只改 Git，不直接使用 kubectl edit 修改线上资源。
