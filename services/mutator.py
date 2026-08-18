# services/mutator.py
import ast
import os
import random
import string
import keyword
import time
import shutil
from pathlib import Path


class PythonObfuscator(ast.NodeTransformer):
    """Renomme variables et fonctions aléatoirement."""
    def __init__(self, seed=None):
        self.rng = random.Random(seed)
        self.scopes = [{}]
        self.reserved = set(keyword.kwlist) | {"self", "cls"}
        self.func_counter = 0

    def _random_name(self):
        while True:
            name = "_" + "".join(self.rng.choices(string.ascii_letters + string.digits, k=10))
            if name not in self.reserved:
                return name

    def _enter_scope(self):
        self.scopes.append({})

    def _leave_scope(self):
        self.scopes.pop()

    def _declare(self, name):
        if not name or name in self.reserved or name.startswith("__"):
            return name
        current = self.scopes[-1]
        if name not in current:
            current[name] = self._random_name()
        return current[name]

    def _lookup(self, name):
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return name

    def visit_FunctionDef(self, node):
        node.name = self._declare(node.name)
        self._enter_scope()
        for arg in node.args.args:
            arg.arg = self._declare(arg.arg)
        node.body = [self.visit(stmt) for stmt in node.body]
        self._leave_scope()
        return node

    def visit_ClassDef(self, node):
        node.name = self._declare(node.name)
        self._enter_scope()
        node.body = [self.visit(stmt) for stmt in node.body]
        self._leave_scope()
        return node

    def visit_Name(self, node):
        node.id = self._lookup(node.id)
        return node


class CodeMutator:
    """Génère une version mutée du code source."""
    def __init__(self):
        self.rng = random.Random()

    def mutate(self, source_file: Path, mutation_level: int = 1) -> Path:
        """
        Crée un nouveau fichier muté à partir de source_file.
        Retourne le chemin du nouveau fichier.
        """
        source_path = Path(source_file)
        if not source_path.exists():
            raise FileNotFoundError(f"Source introuvable: {source_path}")

        # Lire le code source
        source = source_path.read_text(encoding='utf-8')

        # Niveau de mutation 1 : obfuscation AST
        if mutation_level >= 1:
            try:
                tree = ast.parse(source)
                transformer = PythonObfuscator(seed=int(time.time()))
                tree = transformer.visit(tree)
                ast.fix_missing_locations(tree)
                source = ast.unparse(tree)
            except Exception as e:
                # En cas d'erreur, on continue sans obfuscation
                pass

        # Niveau 2 : ajout de code mort
        if mutation_level >= 2:
            source = self._add_dead_code(source)

        # Niveau 3 : ajout d'anti-debug
        if mutation_level >= 3:
            source = self._add_anti_debug(source)

        # Générer un nom de fichier aléatoire
        new_name = f"mutated_{int(time.time())}_{self.rng.randint(1000,9999)}.py"
        new_path = source_path.parent / new_name

        # Écrire le nouveau fichier
        new_path.write_text(source, encoding='utf-8')

        # Rendre exécutable sous Unix (optionnel)
        if hasattr(os, 'chmod'):
            os.chmod(new_path, 0o755)

        return new_path

    def _add_dead_code(self, source: str) -> str:
        """Ajoute des branches inutiles sans casser l'indentation."""
        lines = source.split('\n')
        dead_templates = [
            "if False: pass",
            "if 1 == 2: pass",
            "while False: break",
            "x = 0\nif x > 1: pass",
        ]
        new_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            new_lines.append(line)
            # Ajouter après les imports, définitions, etc.
            stripped = line.strip()
            if (stripped.startswith(('import ', 'from ')) or
                stripped.startswith(('def ', 'class ')) or
                stripped.endswith(':')):
                if self.rng.random() < 0.15:
                    dead_line = self.rng.choice(dead_templates)
                    indent = len(line) - len(line.lstrip())
                    if stripped.endswith(':'):
                        indent += 4
                    dead_line = ' ' * indent + dead_line
                    new_lines.append(dead_line)
            i += 1
        return '\n'.join(new_lines)

    def _add_anti_debug(self, source: str) -> str:
        """Préfixe le code par des checks anti-debug."""
        anti_debug = '''import sys
import os

def _anti_debug():
    if hasattr(sys, 'gettrace') and sys.gettrace() is not None:
        sys.exit(0)
    if os.name == 'nt':
        try:
            import ctypes
            if ctypes.windll.kernel32.IsDebuggerPresent() != 0:
                sys.exit(0)
        except:
            pass

_anti_debug()

'''
        return anti_debug + source