# Argo CD 使用文档

本项目通过 Argo CD 把 Git 仓库 `k8s/` 目录中的资源部署到 Docker Desktop 的 Kubernetes。第一次搭建按第 1 至 3 节执行；以后主要看第 4、5 节。普通发布不需要安装 Argo CD 命令行工具，也不需要手工点 `Sync`。

## 1. 安装前确认

先启动 Docker Desktop 并启用 Kubernetes。打开 PowerShell，执行：

```powershell
kubectl config use-context docker-desktop
kubectl config current-context
kubectl get nodes
```

确认当前 context 是 `docker-desktop`，节点状态为 `Ready`。以下安装命令会修改当前集群，不要跳过 context 检查。如果已经能运行 `kubectl -n argocd get application hello-k8s`，无需重复安装，直接看第 4 节。

## 2. 第一次安装 Argo CD

官方安装方式会从 GitHub 下载清单，因此需要能访问 `raw.githubusercontent.com`，集群还需要能拉取 Argo CD 的镜像。运行：

```powershell
kubectl create namespace argocd
kubectl apply -n argocd --server-side --force-conflicts -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl -n argocd rollout status deployment/argocd-server --timeout=5m
kubectl -n argocd rollout status deployment/argocd-repo-server --timeout=5m
kubectl -n argocd rollout status statefulset/argocd-application-controller --timeout=5m
kubectl -n argocd get pods
```

预期两个 Deployment 和一个 StatefulSet 成功滚动更新，Argo CD Pod 的 `READY` 列分子等于分母、`STATUS` 为 `Running`。若某个组件提示找不到，先执行 `kubectl -n argocd get deployment,statefulset`，以实际资源类型检查。首次拉取镜像可能需要几分钟。`--server-side --force-conflicts` 是官方安装清单所需的应用方式。

已有 `argocd` 命名空间但安装未完成时，不要再执行 `kubectl create namespace argocd`；从 `kubectl apply ...` 那行继续。生产环境应固定安装清单的版本；这里使用官方 `stable` 分支仅用于本地学习。

## 3. 注册本项目

进入克隆好的 `hello-k8s-cicd` 项目根目录，先确认文件存在、内容指向本项目：

```powershell
Get-Location
Get-Content .\argocd-application.yaml
kubectl apply -f .\argocd-application.yaml
kubectl -n argocd get application hello-k8s
```

`argocd-application.yaml` 中应有 `repoURL: https://github.com/zsong0348-pixel/hello-k8s-cicd.git`、`targetRevision: main`、`path: k8s`，目标 namespace 为 `hello`。这个 `apply` 只在第一次注册或修改 Application 配置后需要执行。Application 配置文件本身在仓库根目录，**不在** Argo CD 正在同步的 `k8s/` 路径中；只推送这个文件不会自动更新已经注册的 Application。

等待自动同步，再执行：

```powershell
kubectl -n argocd get application hello-k8s
kubectl -n hello get deployment,pods,service
kubectl -n hello rollout status deployment/hello-k8s --timeout=5m
```

预期 Application `Synced / Healthy`、Deployment `2/2`、两个 Pod `1/1 Running`。刚注册时的 `OutOfSync` 或 `Progressing` 可以是暂态。若长时间无法就绪，按第 5 节检查。

## 4. 日常查看和登录界面

普通发布后运行 `kubectl -n argocd get application hello-k8s` 就能看同步和健康状态。需要在界面查看资源或错误时，另开 PowerShell：

```powershell
kubectl -n argocd port-forward svc/argocd-server 8080:443
```

保持窗口打开，浏览器访问 `https://localhost:8080`。本地自签名证书可能触发浏览器警告，确认访问的是自己启动的 `localhost` 后继续。

首次登录的用户名是 `admin`。再开一个 PowerShell 获取初始密码：

```powershell
$encoded = kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}"
[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($encoded))
```

使用第二行输出的明文密码，不能把第一行的 Base64 结果直接填进登录框。初始 Secret 可能在管理员改密后被删除；如果它不存在，应找现有管理员获取账号，不要重装 Argo CD。

登录后点击 `hello-k8s`，看顶部的 `SYNC STATUS` 和 `HEALTH STATUS`，再看下面的 Namespace、Service、Deployment 资源图。点击异常资源可查看状态、事件和差异。常见状态：

| 状态 | 含义与动作 |
|---|---|
| `Synced / Healthy` | Git 与集群一致，业务资源健康。 |
| `OutOfSync` | Git 与集群暂不一致；刚推送时等待自动同步，持续存在再查同步错误。 |
| `Synced / Progressing` | 已同步配置，但新 Pod 仍在创建或探针尚未通过。 |
| `Degraded` | 资源异常；查看异常资源、Pod 事件和日志。 |
| `Unknown` | Argo 暂时无法判断；检查控制器、仓库连接及网络。 |

本项目已配置自动同步、`prune` 和 `selfHeal`。因此不要在界面随意执行 `Delete`、`Prune`、`Rollback` 或修改线上资源。日常更新由 GitHub Actions 改 Git，Argo CD 再自动部署。关闭端口转发窗口后，界面地址不再可用，但 Argo CD 本身仍在集群内运行。

## 5. 同步异常时逐步检查

先看 Application 的详细状态和事件：

```powershell
kubectl -n argocd describe application hello-k8s
kubectl -n argocd get pods
kubectl -n hello get deployment,pods
kubectl -n hello get events --sort-by=.lastTimestamp
```

若界面显示仓库读取失败，核对 `repoURL`、`targetRevision`、`path`，并确认 Argo CD 所在环境能访问 GitHub。这个仓库是 Public，默认无需仓库凭证；Private 仓库需要单独配置凭证。若无法拉镜像，先获取真实 Pod 名，再看 Events 中的 GHCR 错误，确认 Package 为 Public、镜像地址存在：

```powershell
$podName = kubectl -n hello get pods -l app=hello-k8s -o jsonpath="{.items[0].metadata.name}"
kubectl -n hello describe pod $podName
```

若为 `Synced / Progressing` 或 `Degraded`，检查滚动更新与应用日志：

```powershell
kubectl -n hello rollout status deployment/hello-k8s --timeout=5m
kubectl -n hello get pods
kubectl -n hello describe deployment hello-k8s
$podName = kubectl -n hello get pods -l app=hello-k8s -o jsonpath="{.items[0].metadata.name}"
kubectl -n hello logs $podName
```

没有 Pod 时先查 Deployment 和 Events。若是 `ImagePullBackOff`，查镜像权限和网络；若是 `CrashLoopBackOff`，看日志；若是探针失败，检查 `/healthz` 是否能返回 HTTP 200。

若 Actions 已成功而 Argo 仍显示旧版本，比较 GitHub 上最新 `k8s/deployment.yaml` 的镜像 SHA 和集群中的镜像：

```powershell
kubectl -n hello get deployment hello-k8s -o jsonpath="{.spec.template.spec.containers[0].image}"
kubectl -n argocd get application hello-k8s
```

确认 Actions 确实生成了 `chore: deploy ...` 提交。Argo CD 默认按周期检测 Git，刚推送时先等待；持续不更新时看 Application 的 `describe` 中的 `Conditions` 和 `Events`。在界面按 `Refresh` 可重新读取状态；只有明确诊断后才考虑人工 `Sync`，因为本项目本应自动同步。不要手工 `kubectl apply -f k8s/` 绕过 Argo CD。

## 6. 回滚和停止使用

回滚遵循 [01-使用文档](01-使用文档.md) 第 7 节的 Git 流程。由于 `selfHeal` 已开启，直接在集群中运行 `kubectl rollout undo` 无法作为持久回滚；Argo CD 会恢复 Git 中的版本。

只是不想打开 Argo 界面时，关闭 `port-forward` 窗口即可，**不要删除 Application**。删除 Application、`argocd` 或 `hello` 命名空间会影响部署或业务资源；本地学习环境也应先确认是否仍需要这些资源。

参考：[Argo CD 官方入门安装文档](https://argo-cd.readthedocs.io/en/stable/getting_started/)、[自动同步说明](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/)。
