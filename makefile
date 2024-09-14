.ONESHELL:
remove:
	poetry env remove --all
	ls | grep -xv "makefile" | xargs rm -rf
