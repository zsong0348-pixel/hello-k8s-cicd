# hello-k8s-cicd

Windows 本地 Kubernetes + GitHub Actions + GHCR + Argo CD CI/CD 示例。

## 文档

1. [傻瓜式使用文档](docs/01-使用文档.md)
2. [GitHub 与部署配置详解](docs/02-GitHub配置详解.md)
3. [文档目录](docs/README.md)

第一次使用请从“傻瓜式使用文档”开始，不要跳步。

## 流程

```text
代码提交 -> GitHub Actions -> GHCR -> Git 配置更新 -> Argo CD -> Kubernetes
```
