SHELL := /bin/sh

SITE ?= lawfirm-staging
BUNDLE_DIR ?= dist/bundle-$(SITE)
SSH ?=
SUDO ?= sudo
REMOTE_BUNDLE ?= $(if $(SSH),bundle,$(BUNDLE_DIR))
PYTHON ?= python3
QUILLO_RELEASE_DIR ?=
QUILLO_RELEASE_SHA256 ?=
COMPOSE_BIN ?=
export QUILLO_RELEASE_DIR QUILLO_RELEASE_SHA256 COMPOSE_BIN

.PHONY: help survey bundle install verify test

help:
	@echo "make survey  [SSH='ssh fde@may-khach'] [SITE=...]   khảo sát máy khách, preflight so với REQUIREMENTS"
	@echo "make bundle  SITE=... QUILLO_RELEASE_DIR=...         dựng bundle offline vào BUNDLE_DIR"
	@echo "make install [SSH=...] [REMOTE_BUNDLE=...]           cài từ bundle đã chép sang máy khách"
	@echo "make verify  [SSH=...] [REMOTE_BUNDLE=...]           kiểm quillo đang chạy đúng"
	@echo "make test                                            test của chính repo này"

survey:
	$(SSH) sh -s < survey/site_survey.sh > reports/survey-$(SITE).json.tmp
	mv reports/survey-$(SITE).json.tmp reports/survey-$(SITE).json
	$(PYTHON) survey/preflight.py reports/survey-$(SITE).json survey/REQUIREMENTS.yaml > reports/preflight-$(SITE).json; \
	rc=$$?; cat reports/preflight-$(SITE).json; exit $$rc

bundle:
	sh delivery/build_bundle.sh "$(SITE)" "$(BUNDLE_DIR)"

install:
	$(SSH) $(SUDO) bash $(REMOTE_BUNDLE)/install.sh

verify:
	$(SSH) sh $(REMOTE_BUNDLE)/verify.sh

test:
	$(PYTHON) -m pytest -q tests
