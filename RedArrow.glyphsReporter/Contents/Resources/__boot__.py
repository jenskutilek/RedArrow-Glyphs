import GlyphsApp
from GlyphsApp import Glyphs

def _run(*scripts):
	global __file__
	import os, sys
	sys.frozen = 'macosx_plugin'
	base = os.environ['RESOURCEPATH']
	for script in scripts:
		path = os.path.join(base, script)
		__file__ = path
		execfile(path, globals(), globals())

if hasattr(Glyphs, 'versionNumber') and Glyphs.versionNumber >= 2.3:
	_run('RedArrow.py')
else:
	_run('RedArrow22.py')