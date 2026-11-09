from pathlib import Path
from streamlit.testing.v1 import AppTest


def button(app, label):
    next(b for b in app.button if b.label == label).click().run()
    assert not app.exception


def stage(app, label):
    next(r for r in app.radio if r.label == 'Flujo de trabajo').set_value(label).run()
    assert not app.exception


def test_synthetic_ui():
    app = AppTest.from_file(str(Path(__file__).parents[1] / 'app.py'), default_timeout=30).run()
    assert not app.exception
    button(app, 'Generar fachada nueva')
    stage(app, '2 · Limpiar')
    button(app, 'Previsualizar')
    button(app, 'Confirmar limpieza')
    stage(app, '3 · Normales')
    button(app, 'Estimar normales')
    stage(app, '4 · Segmentar')
    button(app, 'Segmentar')
    stage(app, '5 · Reconstruir')
    button(app, 'Reconstruir Ball Pivoting')
    assert len(app.session_state['mesh'].triangles) > 100
    assert 'undo' not in app.session_state
    assert len(app.session_state['cloud'].xyz) <= 50000


def test_gallery_is_precomputed():
    app = AppTest.from_file(str(Path(__file__).parents[1] / 'app.py'), default_timeout=30).run()
    assert not app.exception
    button(app, 'Ver resultado')
    assert len(app.session_state['mesh'].triangles) > 0
