Attempt to create an - as much as possible automated - workflow for typical SFX data processing. Takes ideas from the crystfel_spb_tutorial as well as previous pipeline attempts.

Tentative instructions:

1. use the *https* link on the project front page to clone, or download from  
   there directly.
2. move into the cloned repository folder and ``git checkout dev``
3. move into the ``bin`` subfolder, and open ``extra-xwiz`` with a text editor.
4. edit the line ``sys.path.append('/home/dallanto/Devel/Prototypes/EXtra-xwiz')``  
   so that the path string inside the brackets is ``'/path/to/your/repository'``
5. make sure you use EuXFEL-Anaconda3: ``module load exfel exfel_anconda3``  
   This should provide support for all the required Python modules
6. Only in case you lack the module ``toml`` nonetheless:  
   ``python -m pip install --user toml``

