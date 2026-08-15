# Myrmex Testing Guide

Dieses Dokument beschreibt, wie man die Tests im Myrmex-Projekt ausführt und welche Test-Konventionen gelten.

## Voraussetzungen

- Python 3.12+
- pytest >= 8.0.0
- Alle Abhängigkeiten aus `requirements.txt`

## Tests ausführen

### Alle Tests ausführen

```bash
cd myrmex
python -m pytest tests/ -v
```

### Tests mit Details

```bash
python -m pytest tests/ -vv --tb=long
```

### Spezifische Test-Datei

```bash
python -m pytest tests/test_theorist.py -v
```

### Spezifische Test-Klasse

```bash
python -m pytest tests/test_theorist.py::TestTheoristConsolidation -v
```

### Spezifischer Test

```bash
python -m pytest tests/test_theorist.py::TestTheoristConsolidation::test_consolidates_knowledge_pheromones -v
```

### Tests mit Coverage (wenn pytest-cov installiert)

```bash
python -m pytest tests/ --cov=src --cov-report=html
```

## pytest-Konfiguration

Die pytest-Konfiguration befindet sich in `pytest.ini`:

```ini
[pytest]
addopts = -p no:libtmux
```

Das `libtmux`-Plugin wird explizit deaktiviert, um Konflikte zu vermeiden.

## Test-Isolation

### Registry-Reset

Die `CasteRegistry` ist ein Singleton. Um Test-Isolation zu gewährleisten, wird vor jedem Test die Registry zurückgesetzt:

```python
@pytest.fixture(autouse=True)
def reset_registry_before_each_test():
    from src.castes.registry import reset_registry
    reset_registry()
    yield
    reset_registry()
```

### Temporäre Workspaces

Tests verwenden temporäre Workspaces, die nach jedem Test automatisch bereinigt werden:

```python
@pytest.fixture
def temp_workspace():
    temp_dir = tempfile.mkdtemp()
    workspace_path = Path(temp_dir) / "workspace"
    workspace_path.mkdir()
    
    # Benötigte Verzeichnisse erstellen
    (workspace_path / "00_System").mkdir(parents=True)
    (workspace_path / "01_Pheromon_Field").mkdir(parents=True)
    # ... weitere Verzeichnisse
    
    yield workspace_path
    
    shutil.rmtree(temp_dir, ignore_errors=True)
```

## Test-Konventionen

### Naming

- Test-Dateien: `test_*.py`
- Test-Klassen: `Test*` (z.B. `TestTheoristCasteDefinition`)
- Test-Funktionen: `test_*` (z.B. `test_caste_name_is_theorist`)

### Struktur

Tests sind in Klassen gruppiert:

```python
class TestTheoristCasteDefinition:
    """Tests für die Kasten-Definition."""
    
    def test_caste_name_is_theorist(self):
        assert TheoristCaste.caste_name == CasteName.THEORIST


class TestTheoristConsolidation:
    """Tests für die Konsolidierungs-Logik."""
    
    def test_consolidates_knowledge_pheromones(self, theorist, temp_workspace, knowledge_pheromones):
        # Test-Logik hier
        pass
```

### Fixtures

Fixtures sollten aussagekräftige Namen haben und dokumentiert sein:

```python
@pytest.fixture
def knowledge_pheromones(theorist):
    """Erstellt TRAIL-Pheromone mit Knowledge-Tags im gleichen Feld wie die TheoristCaste."""
    # Fixture-Logik hier
```

### Assertions

Verwende aussagekräftige Assertions mit klaren Nachrichten:

```python
assert result.success is True
assert result.pheromones_read > 0, "Sollte Knowledge-Pheromone gelesen haben"
assert theory_path.exists(), "theory_baseline.md sollte erstellt worden sein"
```

## Bekannte Probleme

### Fixture-Ordering

Wenn ein Fixture von einem anderen Fixture abhängt, muss das abhängige Fixture als Parameter übergeben werden:

```python
@pytest.fixture
def knowledge_pheromones(theorist):  # hängt von theorist ab
    field = theorist.pheromone_field  # verwendet das gleiche Feld
    # ...
```

### Singleton-State

Singletons wie `get_registry()` müssen zwischen Tests zurückgesetzt werden, um State-Leaks zu vermeiden.

## Debugging

### Einzelnen Test debuggen

```bash
python -m pytest tests/test_theorist.py::TestTheoristConsolidation::test_consolidates_knowledge_pheromones -v -s
```

### Logging anzeigen

```bash
python -m pytest tests/ -v --log-cli-level=INFO
```

### Nach fehlgeschlagenem Test stoppen

```bash
python -m pytest tests/ -x
```

## Test-Berichte

### JUnit-XML für CI

```bash
python -m pytest tests/ --junitxml=test-results.xml
```

### HTML-Bericht (wenn pytest-html installiert)

```bash
python -m pytest tests/ --html=report.html
```
