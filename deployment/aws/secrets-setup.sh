#!/bin/bash

# AWS Secrets Manager Setup Script
set -e

AWS_REGION=${AWS_REGION:-"us-east-1"}
PROJECT_NAME="isa-mcp"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

echo_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to create a secret
create_secret() {
    local secret_name=$1
    local description=$2
    
    echo_info "Creating secret: $secret_name"
    
    # Check if secret already exists
    if aws secretsmanager describe-secret --secret-id "$secret_name" --region "$AWS_REGION" &>/dev/null; then
        echo_warn "Secret $secret_name already exists, skipping creation"
        return 0
    fi
    
    # Create the secret with a placeholder value
    aws secretsmanager create-secret \
        --name "$secret_name" \
        --description "$description" \
        --secret-string "PLACEHOLDER_VALUE_PLEASE_UPDATE" \
        --region "$AWS_REGION" > /dev/null
    
    echo_info "Created secret: $secret_name (please update with actual value)"
}

# Function to update a secret value
update_secret() {
    local secret_name=$1
    local secret_value=$2
    
    if [[ -z "$secret_value" || "$secret_value" == "PLACEHOLDER_VALUE_PLEASE_UPDATE" ]]; then
        echo_warn "Skipping update for $secret_name (empty or placeholder value)"
        return 0
    fi
    
    echo_info "Updating secret: $secret_name"
    aws secretsmanager update-secret \
        --secret-id "$secret_name" \
        --secret-string "$secret_value" \
        --region "$AWS_REGION" > /dev/null
}

# Main function to setup all secrets
setup_secrets() {
    echo_info "Setting up AWS Secrets Manager secrets for $PROJECT_NAME"
    
    # Core application secrets
    create_secret "$PROJECT_NAME/database-url" "Supabase database connection URL"
    create_secret "$PROJECT_NAME/redis-url" "Redis connection URL"
    create_secret "$PROJECT_NAME/jwt-secret" "JWT signing secret key"
    
    # Supabase secrets
    create_secret "$PROJECT_NAME/supabase-url" "Supabase project URL"
    create_secret "$PROJECT_NAME/supabase-service-key" "Supabase service role key"
    
    # Auth0 secrets
    create_secret "$PROJECT_NAME/auth0-domain" "Auth0 domain"
    create_secret "$PROJECT_NAME/auth0-audience" "Auth0 API audience"
    create_secret "$PROJECT_NAME/auth0-client-id" "Auth0 client ID"
    create_secret "$PROJECT_NAME/auth0-client-secret" "Auth0 client secret"
    
    # Stripe secrets
    create_secret "$PROJECT_NAME/stripe-secret-key" "Stripe secret key"
    create_secret "$PROJECT_NAME/stripe-webhook-secret" "Stripe webhook secret"
    create_secret "$PROJECT_NAME/stripe-pro-price-id" "Stripe Pro tier price ID"
    create_secret "$PROJECT_NAME/stripe-enterprise-price-id" "Stripe Enterprise tier price ID"
    
    # Neo4j secrets (if using)
    create_secret "$PROJECT_NAME/neo4j-uri" "Neo4j connection URI"
    create_secret "$PROJECT_NAME/neo4j-username" "Neo4j username"
    create_secret "$PROJECT_NAME/neo4j-password" "Neo4j password"
    
    # Modal Cloud secrets (for GPU inference)
    create_secret "$PROJECT_NAME/modal-token-id" "Modal Cloud token ID"
    create_secret "$PROJECT_NAME/modal-token-secret" "Modal Cloud token secret"
    
    # Cloudflare secrets (for storage)
    create_secret "$PROJECT_NAME/cloudflare-account-id" "Cloudflare account ID"
    create_secret "$PROJECT_NAME/cloudflare-api-token" "Cloudflare API token"
    create_secret "$PROJECT_NAME/cloudflare-bucket-name" "Cloudflare R2 bucket name"
    
    # Monitoring secrets
    create_secret "$PROJECT_NAME/sentry-dsn" "Sentry DSN for error tracking"
    create_secret "$PROJECT_NAME/datadog-api-key" "Datadog API key for monitoring"
    
    echo_info "All secrets created successfully!"
    echo_warn "Please update the secret values in AWS Secrets Manager console or using AWS CLI:"
    echo "aws secretsmanager update-secret --secret-id '$PROJECT_NAME/database-url' --secret-string 'your-actual-value'"
}

# Function to load secrets from .env file
load_from_env() {
    local env_file=${1:-".env.aws"}
    
    if [[ ! -f "$env_file" ]]; then
        echo_error "Environment file $env_file not found"
        echo_info "Please create $env_file based on .env.aws.template"
        exit 1
    fi
    
    echo_info "Loading secrets from $env_file"
    
    # Source the environment file
    set -a
    source "$env_file"
    set +a
    
    # Update secrets with values from environment file
    update_secret "$PROJECT_NAME/database-url" "$DATABASE_URL"
    update_secret "$PROJECT_NAME/redis-url" "$REDIS_URL"
    update_secret "$PROJECT_NAME/jwt-secret" "$JWT_SECRET_KEY"
    update_secret "$PROJECT_NAME/supabase-url" "$NEXT_PUBLIC_SUPABASE_URL"
    update_secret "$PROJECT_NAME/supabase-service-key" "$SUPABASE_SERVICE_ROLE_KEY"
    update_secret "$PROJECT_NAME/auth0-domain" "$AUTH0_DOMAIN"
    update_secret "$PROJECT_NAME/auth0-audience" "$AUTH0_AUDIENCE"
    update_secret "$PROJECT_NAME/auth0-client-id" "$AUTH0_CLIENT_ID"
    update_secret "$PROJECT_NAME/auth0-client-secret" "$AUTH0_CLIENT_SECRET"
    update_secret "$PROJECT_NAME/stripe-secret-key" "$STRIPE_SECRET_KEY"
    update_secret "$PROJECT_NAME/stripe-webhook-secret" "$STRIPE_WEBHOOK_SECRET"
    update_secret "$PROJECT_NAME/stripe-pro-price-id" "$STRIPE_PRO_PRICE_ID"
    update_secret "$PROJECT_NAME/stripe-enterprise-price-id" "$STRIPE_ENTERPRISE_PRICE_ID"
    update_secret "$PROJECT_NAME/neo4j-uri" "$NEO4J_URI"
    update_secret "$PROJECT_NAME/neo4j-username" "$NEO4J_USERNAME"
    update_secret "$PROJECT_NAME/neo4j-password" "$NEO4J_PASSWORD"
    update_secret "$PROJECT_NAME/modal-token-id" "$MODAL_TOKEN_ID"
    update_secret "$PROJECT_NAME/modal-token-secret" "$MODAL_TOKEN_SECRET"
    update_secret "$PROJECT_NAME/cloudflare-account-id" "$CLOUDFLARE_ACCOUNT_ID"
    update_secret "$PROJECT_NAME/cloudflare-api-token" "$CLOUDFLARE_API_TOKEN"
    update_secret "$PROJECT_NAME/cloudflare-bucket-name" "$CLOUDFLARE_BUCKET_NAME"
    update_secret "$PROJECT_NAME/sentry-dsn" "$SENTRY_DSN"
    update_secret "$PROJECT_NAME/datadog-api-key" "$DATADOG_API_KEY"
    
    echo_info "Secrets updated from environment file"
}

# Function to list all secrets
list_secrets() {
    echo_info "Listing all $PROJECT_NAME secrets:"
    aws secretsmanager list-secrets \
        --filters Key=name,Values="$PROJECT_NAME/" \
        --query 'SecretList[].Name' \
        --output table \
        --region "$AWS_REGION"
}

# Main execution
case "${1:-setup}" in
    "setup")
        setup_secrets
        ;;
    "load")
        load_from_env "${2:-.env.aws}"
        ;;
    "list")
        list_secrets
        ;;
    *)
        echo_error "Usage: $0 [setup|load|list] [env-file]"
        echo_info "  setup: Create all required secrets with placeholder values"
        echo_info "  load:  Load secret values from environment file (default: .env.aws)"
        echo_info "  list:  List all project secrets"
        exit 1
        ;;
esac