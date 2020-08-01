import pytest

import nbformat
from jupyter_client.kernelspec import NoSuchKernel

from ploomber.tasks.Params import Params
from ploomber.sources.NotebookSource import NotebookSource, is_python
from ploomber.products import File
from ploomber.exceptions import RenderError

notebook_ab = """
# + tags=['parameters']
a = 1
b = 2
product = None

# +
a + b
"""


def test_error_if_kernelspec_name_is_invalid():
    with pytest.raises(NoSuchKernel):
        NotebookSource(notebook_ab,
                       ext_in='py',
                       kernelspec_name='invalid_kernelspec')


def test_error_if_parameters_cell_doesnt_exist():
    notebook_no_parameters_tag = """
x = 1
    """

    source = NotebookSource(notebook_no_parameters_tag,
                            ext_in='py',
                            kernelspec_name='python3',
                            static_analysis=True)

    params = Params()
    # set private attribute to allow init with product
    params._dict = {'product': File('output.ipynb')}

    with pytest.raises(RenderError) as excinfo:
        source.render(params)

    assert ('\nNotebook does not have a cell tagged "parameters"' == str(
        excinfo.value))


# add test on missing kernelspec_name


def test_sucess_if_parameters_match():
    source = NotebookSource(notebook_ab,
                            ext_in='py',
                            kernelspec_name='python3',
                            static_analysis=True)

    params = Params()
    params._dict = {'product': File('output.ipynb'), 'a': 1, 'b': 2}
    source.render(params)


def test_warn_if_using_default_value():
    source = NotebookSource(notebook_ab,
                            ext_in='py',
                            kernelspec_name='python3',
                            static_analysis=True)

    params = Params()
    params._dict = {'product': File('output.ipynb'), 'a': 1}

    with pytest.warns(UserWarning) as record:
        source.render(params)

    assert len(record) == 1
    assert (str(record[0].message) ==
            "Missing parameters: {'b'}, will use default value")


def test_error_if_passing_undeclared_parameter():
    source = NotebookSource(notebook_ab,
                            ext_in='py',
                            kernelspec_name='python3',
                            static_analysis=True)

    params = Params()
    params._dict = {'product': File('output.ipynb'), 'a': 1, 'b': 2, 'c': 3}

    with pytest.raises(RenderError) as excinfo:
        source.render(params)

    assert str(excinfo.value) == "\nPassed non-declared parameters: {'c'}"


def test_error_if_using_undeclared_variable():
    notebook_w_warning = """
# + tags=['parameters']
a = 1
b = 2

# +
# variable "c" is used but never declared!
a + b + c
"""
    source = NotebookSource(notebook_w_warning,
                            ext_in='py',
                            kernelspec_name='python3',
                            static_analysis=True)

    params = Params()
    params._dict = {'product': File('output.ipynb'), 'a': 1, 'b': 2}

    with pytest.raises(RenderError) as excinfo:
        source.render(params)

    assert "undefined name 'c'" in str(excinfo.value)


def test_error_if_syntax_error():
    notebook_w_error = """
# + tags=['parameters']
a = 1
b = 2

# +
if
"""
    source = NotebookSource(notebook_w_error,
                            ext_in='py',
                            kernelspec_name='python3',
                            static_analysis=True)

    params = Params()
    params._dict = {'product': File('output.ipynb'), 'a': 1, 'b': 2}

    with pytest.raises(RenderError) as excinfo:
        source.render(params)

    assert 'invalid syntax' in str(excinfo.value)


def test_error_if_no_parameters_cell():
    source = """
1 + 1
    """

    source = NotebookSource(source,
                            ext_in='py',
                            kernelspec_name='python3',
                            static_analysis=True)

    params = Params()
    params._dict = {'product': File('output.ipynb'), 'a': 1, 'b': 2}

    with pytest.raises(RenderError) as excinfo:
        source.render(params)

    assert 'Notebook does not have a cell tagged "parameters"' in str(
        excinfo.value)


def test_injects_parameters_on_render():
    s = NotebookSource("""
# + tags=['parameters']
product = None
some_param = 2
    """,
                       ext_in='py',
                       kernelspec_name='python3')
    params = Params()
    params._dict = {'some_param': 1, 'product': File('output.ipynb')}
    s.render(params)

    nb = nbformat.reads(s.rendered_nb_str, as_version=nbformat.NO_CONVERT)

    # cell 0: empty
    # cell 1: parameters
    # cell 2: injected-parameters

    injected = nb.cells[2]
    tags = injected['metadata']['tags']

    assert len(tags) == 1
    assert tags[0] == 'injected-parameters'

    # py 3.5 does not gurantee order, so we check them separately
    assert 'some_param = 1' in injected['source']
    assert 'product = "output.ipynb"' in injected['source']


def test_cleanup_rendered_notebook():
    # simulate a rendered notebook (with injected parameters)
    source = """
1 + 1
    """

    source = NotebookSource(source, ext_in='py', kernelspec_name='python3')
    params = Params()
    params._dict = {'product': File('output.ipynb')}
    source.render(params)


# extracting language from notebook objects


def nb_python_meta():
    nb = nbformat.v4.new_notebook()
    nb.metadata = {'kernel_info': {'language': 'python'}}
    return nb


def nb_python_inferred():
    nb = nbformat.v4.new_notebook()
    nb.metadata = {'kernel_info': {'language': 'python'}}
    code = nbformat.v4.new_code_cell(source='1+1')
    nb.cells.append(code)
    return nb


def nb_R_meta():
    nb = nbformat.v4.new_notebook()
    nb.metadata = {'kernel_info': {'language': 'R'}}
    return nb


@pytest.mark.parametrize('nb, expected', [(nb_python_meta(), True),
                                          (nb_python_inferred(), True),
                                          (nb_R_meta(), False)])
def test_infer_language(nb, expected):
    assert is_python(nb) is expected


def nb_unknown(metadata):
    # second most popular case is R, but we don't have a way to know for sure
    nb = nbformat.v4.new_notebook()
    nb.metadata = metadata
    code = nbformat.v4.new_code_cell(source='a <- 1')
    nb.cells.append(code)
    return nb


@pytest.mark.parametrize('nb', [
    nb_unknown({}),
    nb_unknown({'kernel_info': {}}),
])
def test_error_with_unknown_language(nb):
    assert not is_python(nb)


nb_case_1 = """
# + tags=["parameters"]
upstream = {'some_key': 'some_value'}
""", ['some_key']

nb_case_2 = """
# + tags=["parameters"]
upstream = {'a': None, 'b': None}
""", ['a', 'b']


@pytest.mark.parametrize('code, expected', [nb_case_1, nb_case_2])
def test_extract_upstream_from_parameters(code, expected):
    source = NotebookSource(code, ext_in='py', kernelspec_name='python3')
    upstream = source.extract_upstream()
    assert sorted(upstream) == sorted(expected)