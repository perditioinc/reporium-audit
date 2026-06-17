# Root passthrough to the $0/OSS local dev substrate in local/.
# Lets you run `make local-up` etc. from the repo root.
#
#   make local-up      # start the local OSS substitutes (nginx + postgres)
#   make local-smoke   # run the real audit against the substitutes
#   make local-down    # tear everything down (containers + volumes)

LOCAL_DIR := local

.PHONY: local-up local-smoke local-down local-seed local-teardown local-logs

local-up: ## Start the local OSS substrate
	$(MAKE) -C $(LOCAL_DIR) up

local-smoke: ## Run the real audit against the local substrate
	$(MAKE) -C $(LOCAL_DIR) smoke

local-down: ## Tear down the local substrate (containers + volumes)
	$(MAKE) -C $(LOCAL_DIR) down

local-seed: ## Generate fixtures + .env for the local substrate
	$(MAKE) -C $(LOCAL_DIR) seed

local-teardown: ## Full teardown of the local substrate
	$(MAKE) -C $(LOCAL_DIR) teardown

local-logs: ## Tail local substrate logs
	$(MAKE) -C $(LOCAL_DIR) logs
