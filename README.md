Attempt to create an - as much as possible automated - workflow for typical SFX data processing. Takes ideas from the crystfel_spb_tutorial as well as previous pipeline attempts.

Tentative instructions:

1. use the *https* link on the project front page to clone, or download from  
   there directly.
2. move into the cloned repository folder and ``git checkout dev_cellexplorer``
3. make sure you use EuXFEL-Anaconda3: ``module load exfel exfel_anconda3``  
4. type ``pip install --user -e .`` (still in the repository parent folder)
5. export PATH="/home/<your_name>/.local/bin:$PATH"

Explanations:

Installation with ``pip --user`` will install to your home folder, and ``-e`` will create a dynamic link from there to the downloaded repository.
- the egg-link is in  ``~/.local/lib/python3.7/site-packages``
- command-line tools are in ``~/.local/bin``

Practically, you want have the "bin" folder in your search path, so that you can easily call ``xwiz-workflow`` from everywhere. That's why the command of step (5.) is best done in your ``~/.bashrc``, ``~/.zshrc`` etc, and needs to be done only once.

