.PHONY: check
check:
	ln -sf easierocd.py _xxx_tmp.py
	nosetests-3.3 -v --with-doctest easierocd easierocd.arm _xxx_tmp.py

.PHONY: clean
clean:
	rm -f _xxx_tmp.py
