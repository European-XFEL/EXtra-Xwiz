Attempt to create an - as much as possible automated - workflow for typical SFX data processing. Takes ideas from the crystfel_spb_tutorial as well as previous pipeline attempts.

## Tentative instructions:

1. use the *https* link on the project front page to clone, or download from  
   there directly.
2. move into the cloned repository folder and ``git checkout dev``
3. make sure you use EuXFEL-Anaconda3: ``module load exfel exfel_anaconda3``  
4. type ``pip install --user -e .`` (still in the repository parent folder)
5. type ``export PATH="/home/<your_name>/.local/bin:$PATH"`` (or add to
   resource file)
6. Use the main tool: ``xwiz-workflow`` (call from the folder you want to have
   the output files in)

Steps 1 to 5 have to be done only once, in principle.
 
## Explanations:

Installation with ``pip --user`` will install to your home folder, and ``-e``
will create a dynamic link from there to the downloaded repository.

- the egg-link is in  ``~/.local/lib/python3.7/site-packages``
- command-line tools are in ``~/.local/bin``

Practically, you want have the "bin" folder in your search path, so that you
can easily call ``xwiz-workflow`` from everywhere. That's why the step 5 is
best added as command-line in your shell resource file (``~/.bashrc``,
``~/.zshrc`` etc.) and thus it needs to be done only once.

The first run of ``xwiz-workflow`` will only create the configuration from a
template.
It is named ``.xwiz_conf.toml`` and will be written to the present working
folder (PWD, ``.``) i. e. to where the tool was called from.
It is strongly recommeded to revise that configuration file and to replace with
reasonable values, at least the input paths.
 
