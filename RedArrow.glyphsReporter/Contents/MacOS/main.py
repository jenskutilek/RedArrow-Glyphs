def _run(*scripts):
	global __file__
	import os, sys #, site
	sys.frozen = 'macosx_plugin'
	base = os.environ['RESOURCEPATH']
	for script in scripts:
		path = os.path.join(base, script)
		__file__ = path
		execfile(path, globals(), globals())

_run('plugin.py')
