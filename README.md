# Azure AI Terraform (Local LLM + GitHub Actions)

Create Azure resources using simple prompts on your local machine.

Example prompts:
- `create storage account rg_name=dev-rg location="Central India" storage_account_name=aistorage1234`
- `create vm rg_name=dev-rg location="Central India" vm_name=ai-vm vm_size=Standard_B1s`

Flow:
1. Local prompt -> Ollama (Local LLM) -> JSON
2. JSON fills Terraform templates -> env/main.tf
3. Terraform fmt/init/validate locally
4. Git commit/push
5. GitHub Actions runs Terraform apply to create Azure resources

## Repository structure

```
azure-ai-terraform/
├── .github/workflows/terraform.yml
├── env/provider.tf
├── templates/
│   ├── storage.tf.tpl
│   └── vm.tf.tpl
├── local_ai.py
├── .gitignore
└── README.md
```

## Prerequisites

- Terraform installed and in PATH
- Git installed
- Python 3.10+
- Ollama installed
- Azure CLI installed

## Setup Ollama

Install model:
```bash
ollama pull phi3:mini
```

Verify server:
```bash
curl http://127.0.0.1:11434/api/tags
```

## Setup Azure Service Principal for GitHub Actions

Login:
```bash
az login
```

Create SP:
```bash
az ad sp create-for-rbac --name github-terraform-sp --role Contributor --scopes /subscriptions/<SUBSCRIPTION_ID>
```

Add GitHub Secrets (Repo -> Settings -> Secrets and variables -> Actions):
- ARM_CLIENT_ID
- ARM_CLIENT_SECRET
- ARM_SUBSCRIPTION_ID
- ARM_TENANT_ID

## Run locally

```bash
python local_ai.py
```

## Notes

- Storage account name must be lowercase letters+numbers only, 3-24 chars.
- Provider configuration is in `env/provider.tf` only.
- Templates contain only resources.
