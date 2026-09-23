# GitHub 与部署配置详解

本文件逐项解释仓库 zsong0348-pixel/hello-k8s-cicd 的配置。

## 1. 仓库设置

仓库地址：

~~~text
https://github.com/zsong0348-pixel/hello-k8s-cicd
~~~

### 1.1 仓库可见性

路径：Settings -> General -> Danger Zone -> Change repository visibility。

学习环境使用 Public，Argo CD 可以直接读取。生产环境可以使用 Private，但需要给 Argo CD 配置 Deploy Key 或 GitHub App。

### 1.2 GitHub Actions 写入权限

路径：Settings -> Actions -> General -> Workflow permissions。

当前流水线需要自动提交 k8s/deployment.yaml，因此选择 Read and write permissions。没有写权限时，最后的 git push 会出现 403。

### 1.3 Actions 权限

路径：Settings -> Actions -> General -> Actions permissions。

确认仓库允许运行 Actions。本项目使用：

- actions/checkout
- actions/setup-python
- docker/login-action
- docker/build-push-action

### 1.4 main 分支保护

路径：Settings -> Rules -> Rulesets。

团队环境建议：

~~~text
Target branch: main
Require pull request: 开启
Require approvals: 1 或 2
Require status checks: 开启
Block force pushes: 开启
Block deletions: 开启
~~~

当前学习版 workflow 会直接提交 deployment.yaml。启用严格 PR 保护前，应先将自动提交改成自动创建 Pull Request。

## 2. 仓库目录说明

~~~text
hello-k8s-cicd/
├── app.py
├── requirements.txt
├── Dockerfile
├── .dockerignore
├── .github/workflows/ci-cd.yaml
├── k8s/namespace.yaml
├── k8s/deployment.yaml
├── k8s/service.yaml
├── argocd-application.yaml
└── docs/
~~~

| 文件 | 作用 |
|---|---|
| app.py | Flask 应用代码 |
| requirements.txt | Python 依赖和版本 |
| Dockerfile | 构建 Docker 镜像 |
| .dockerignore | 排除不需要放入镜像的文件 |
| ci-cd.yaml | GitHub Actions 流水线 |
| namespace.yaml | 创建 hello 命名空间 |
| deployment.yaml | 声明 Pod、镜像、探针和资源限制 |
| service.yaml | 给 Pod 提供稳定入口 |
| argocd-application.yaml | 告诉 Argo CD 监听哪个仓库 |

## 3. GitHub Actions 触发配置

文件：.github/workflows/ci-cd.yaml。

### 3.1 流程名称

~~~yaml
name: ci-cd
~~~

显示在 Actions 页面。改名只影响显示。

### 3.2 触发条件

~~~yaml
on:
  push:
    branches: [main]
    paths-ignore:
      - 'docs/**'
      - 'README.md'
~~~

推送到 main 时运行，但只修改 docs 目录或 README.md 时不运行。文档变化不影响应用，因此不需要重新构建镜像。

如果还要检查 Pull Request：

~~~yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
~~~

生产项目通常拆成两个 job：PR 只测试，main 才构建发布。

### 3.3 权限

~~~yaml
permissions:
  contents: write
  packages: write
~~~

| 权限 | 原因 |
|---|---|
| contents: write | 自动提交 deployment.yaml |
| packages: write | 推送 GHCR 镜像 |

若不自动提交，contents 应改为 read。

### 3.4 任务和运行系统

~~~yaml
jobs:
  build-publish-deploy:
    runs-on: ubuntu-latest
~~~

GitHub 会创建临时 Ubuntu 虚拟机执行任务，这不是你的本地 Windows。

### 3.5 防止无限循环

~~~yaml
if: github.actor != 'github-actions[bot]'
~~~

流水线会自动提交 deployment.yaml。该条件让机器人提交不再触发构建，避免循环。

## 4. Actions 每个步骤

### 4.1 拉取代码

~~~yaml
- name: Checkout
  uses: actions/checkout@v4
~~~

把仓库下载到临时虚拟机。

### 4.2 Python 环境

~~~yaml
- name: Set up Python
  uses: actions/setup-python@v5
  with:
    python-version: '3.12'
~~~

安装 Python 3.12，和 Dockerfile 的 python:3.12-slim 保持一致。

### 4.3 测试

~~~yaml
- name: Test
  run: |
    python -m pip install -r requirements.txt
    python -c "from app import app; assert app.test_client().get('/healthz').status_code == 200"
~~~

第一行安装依赖，第二行请求健康检查。不是 HTTP 200 时流程立即失败，不会发布。

正式项目示例：

~~~yaml
- name: Test
  run: |
    pip install -r requirements.txt pytest
    pytest
~~~

### 4.4 计算镜像名

~~~yaml
- name: Compute image name
  id: image
  shell: bash
  run: |
    owner=$(echo "${GITHUB_REPOSITORY_OWNER}" | tr '[:upper:]' '[:lower:]')
    echo "name=ghcr.io/${owner}/hello-k8s" >> "$GITHUB_OUTPUT"
~~~

结果是 ghcr.io/zsong0348-pixel/hello-k8s。GHCR 路径转为小写。id: image 让后续步骤可以读取结果。

### 4.5 登录 GHCR

~~~yaml
- name: Log in to GHCR
  uses: docker/login-action@v3
  with:
    registry: ghcr.io
    username: ${{ github.actor }}
    password: ${{ secrets.GITHUB_TOKEN }}
~~~

| 值 | 含义 |
|---|---|
| ghcr.io | GitHub Container Registry |
| github.actor | 触发运行的用户 |
| GITHUB_TOKEN | GitHub 自动生成的临时令牌 |

不需要配置个人密码。禁止把密码或长期 Token 写进 YAML。

### 4.6 构建和推送镜像

~~~yaml
- name: Build and push image
  uses: docker/build-push-action@v6
  with:
    context: .
    push: true
    tags: |
      ${{ steps.image.outputs.name }}:${{ github.sha }}
      ${{ steps.image.outputs.name }}:latest
~~~

| 配置 | 含义 |
|---|---|
| context: . | 使用根目录的 Dockerfile |
| push: true | 构建后推送 GHCR |
| github.sha | 当前提交的唯一版本 |
| latest | 最近构建的快捷标签 |

示例：

~~~text
ghcr.io/zsong0348-pixel/hello-k8s:1f7a1764dda9d44d0d24b1437e324a1fc8561151
ghcr.io/zsong0348-pixel/hello-k8s:latest
~~~

Kubernetes 使用 SHA 版本，保证可以审计和回滚。

### 4.7 更新 Kubernetes 版本

~~~yaml
- name: Update Kubernetes image
  env:
    IMAGE: ${{ steps.image.outputs.name }}
    SHA: ${{ github.sha }}
  run: |
    sed -i -E "s#image: .*#image: ${IMAGE}:${SHA}#" k8s/deployment.yaml
    sed -i -E "s/value: \".*\"/value: \"${SHA}\"/" k8s/deployment.yaml
~~~

它把镜像标签改成当前 Git SHA，同时更新 APP_VERSION。首页的 version 来自该变量。

### 4.8 自动提交部署版本

~~~yaml
- name: Commit deployment change
  run: |
    git config user.name "github-actions[bot]"
    git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
    git add k8s/deployment.yaml
    git diff --cached --quiet || git commit -m "chore: deploy ${GITHUB_SHA} [skip ci]"
    git push
~~~

执行顺序：

1. 设置机器人身份。
2. 选择 deployment.yaml。
3. 有变化时提交。
4. 推送 main。
5. Argo CD 读取并部署。

生产环境更推荐创建 GitOps Pull Request 并人工审核。

## 5. GHCR 配置

### 5.1 镜像位置

GitHub 个人主页 -> Packages -> hello-k8s。

~~~text
ghcr.io/zsong0348-pixel/hello-k8s
~~~

### 5.2 Public 设置

路径：Package settings -> Change visibility -> Public。

Public 镜像允许 Kubernetes 匿名拉取。仓库 Public 不代表 Package 自动 Public，两者分别设置。

### 5.3 Private 镜像示例

生产环境可创建只读拉取 Secret：

~~~powershell
$ghcrToken = "只读GHCR_TOKEN"
kubectl -n hello create secret docker-registry ghcr-pull --docker-server=ghcr.io --docker-username=zsong0348-pixel --docker-password=$ghcrToken
~~~

Deployment 的 spec.template.spec 中加入：

~~~yaml
imagePullSecrets:
  - name: ghcr-pull
containers:
  - name: hello-k8s
~~~

不要把 Token 写进 Git。正式环境使用 External Secrets 或密钥管理系统。

## 6. Dockerfile 配置

~~~dockerfile
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
EXPOSE 8080
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]
~~~

| 配置 | 作用 |
|---|---|
| FROM | 使用精简 Python 3.12 镜像 |
| WORKDIR | 后续命令在 /app 中执行 |
| PYTHONDONTWRITEBYTECODE | 不生成 pyc |
| PYTHONUNBUFFERED | 日志立即输出 |
| COPY requirements | 先复制依赖，利用缓存 |
| RUN pip install | 安装依赖 |
| COPY app.py | 复制程序 |
| EXPOSE 8080 | 声明容器端口 |
| CMD | 使用 gunicorn 启动 |

## 7. Kubernetes 配置

### 7.1 Namespace

~~~yaml
apiVersion: v1
kind: Namespace
metadata:
  name: hello
~~~

hello 是业务隔离空间，查询资源时使用 -n hello。

### 7.2 Deployment 副本

~~~yaml
spec:
  replicas: 2
  selector:
    matchLabels:
      app: hello-k8s
~~~

运行两个 Pod。selector 必须和 Pod 标签一致。

### 7.3 镜像和端口

~~~yaml
containers:
  - name: hello-k8s
    image: ghcr.io/zsong0348-pixel/hello-k8s:GitSHA
    ports:
      - name: http
        containerPort: 8080
~~~

镜像使用 Git SHA，容器内部监听 8080。

### 7.4 健康检查

~~~yaml
readinessProbe:
  httpGet:
    path: /healthz
    port: http
  initialDelaySeconds: 3
  periodSeconds: 5
~~~

Readiness 成功后才接收流量。

~~~yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: http
  initialDelaySeconds: 10
  periodSeconds: 10
~~~

Liveness 持续失败时，Kubernetes 重启容器。

### 7.5 资源限制

~~~yaml
resources:
  requests:
    cpu: 50m
    memory: 64Mi
  limits:
    cpu: 500m
    memory: 256Mi
~~~

requests 是预留量，limits 是上限。50m CPU 等于 0.05 个 CPU 核心。

### 7.6 Service

~~~yaml
spec:
  selector:
    app: hello-k8s
  ports:
    - port: 80
      targetPort: http
  type: ClusterIP
~~~

Service 根据标签找到 Pod，将 80 转到 Pod 的 8080。ClusterIP 仅供集群内部访问，本地浏览器需要 port-forward。

## 8. Argo CD Application 配置

~~~yaml
source:
  repoURL: https://github.com/zsong0348-pixel/hello-k8s-cicd.git
  targetRevision: main
  path: k8s
~~~

| 配置 | 作用 |
|---|---|
| repoURL | Git 仓库地址 |
| targetRevision | 监听 main |
| path | 读取 k8s 目录 |

~~~yaml
destination:
  server: https://kubernetes.default.svc
  namespace: hello
~~~

server 是当前集群，namespace 是业务目标空间。

~~~yaml
syncPolicy:
  automated:
    prune: true
    selfHeal: true
  syncOptions:
    - CreateNamespace=true
~~~

| 配置 | 作用 |
|---|---|
| automated | Git 变化自动同步 |
| prune | Git 删除资源时集群也删除 |
| selfHeal | 手工改集群后恢复为 Git 状态 |
| CreateNamespace | 目标空间不存在时创建 |

第一次注册：

~~~powershell
kubectl apply -f argocd-application.yaml
~~~

之后不用反复 apply，Argo CD 会持续监听。

## 9. Git 操作示例

~~~powershell
git pull --ff-only
git status
git add app.py
git commit -m "feat: change welcome message"
git push
~~~

提交前检查：

~~~powershell
git diff
git diff --cached
~~~

禁止提交：

~~~text
.env
密码文件
GitHub Token
数据库密码
私钥
生产证书
~~~

## 10. 生产环境改造

当前是方便学习的单仓库自动提交方案。生产建议：

~~~text
应用仓库
  -> CI 测试、扫描、构建镜像
  -> CI 创建 GitOps 仓库 PR
  -> 人工审批
  -> Argo CD 同步 staging
  -> 验证
  -> 审批同步 prod
~~~

还应增加：

- Private GHCR 和最小权限。
- 分支保护与 CODEOWNERS。
- 镜像扫描、SBOM 和签名。
- External Secrets 或 Vault。
- Argo CD Project 和 RBAC。
- Ingress、域名和 HTTPS。
- Prometheus、Grafana、日志和告警。
- 数据库兼容迁移和备份恢复。
