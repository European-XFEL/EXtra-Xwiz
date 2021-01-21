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


## UPDATING XWIZ ON THE DA-SW DISTRIBUTION

Xwiz is not part of the general distribution  
(/gpfs/exfel/sw/software/xfel_anaconda3/1.1)  
but lives in a virtual environment based on that "DA-Python"

1. login to Mawell

2. ``ssh xsoft@max-exfl001``

3. one of the two:

 a) New tentative Gitlab download 

```
   git clone ssh://git@git.xfel.eu:10022/dataAnalysis/crystfel_spb_workflow.git
   cd crystfel_spb_workflow
   git checkout dev
```

 b) Update existing local code repo, if already/still existing

```
   cd crystfel_spb_workflow
   git fetch --all
   git checkout dev
   git pull
```

4. ``module load exfel EXtra-xwiz``

   (to verify the correct Python interpreter for 
    the virtual xwiz environment:  
    ``type python``  
    -> /gpfs/exfel/sw/software/extra-xwiz_env/bin/python  
    ``type pip``  
    -> /gpfs/exfel/sw/software/extra-xwiz_env/bin/pip  
   )

5. Given that you are in ~/crystfel_spb_workflow
   and on branch dev

   ``pip install .``

6. remove tentative repo folder on ~ of xsoft (optional)

```
   cd ..
   rm -r crystfel_spb_workflow
```

I typically remove the dev-code folder if I do not plan future updates soon,
because then the xsoft homedir stays clean,
but if we're in a frequent development cycle, one could keep it
in order to follow the fetch/pull approach.

On the other hand, faster development and testing cycles are
probably better done with on the own user-home space with  
``pip install --user -e`` 


