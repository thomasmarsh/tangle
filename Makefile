.PHONY: test

test:
	sh tests/skill.sh
	sh tests/install.sh
	git diff --check
