import json
import sqlite3
from pathlib import Path

PASTA = Path(__file__).parent
CAMINHO_PADRAO = str(PASTA / "clyvo.db")
JSON_PETS = str(PASTA / "pets.json")

ESQUEMA = """
CREATE TABLE IF NOT EXISTS pets (
    id TEXT PRIMARY KEY,
    nome TEXT NOT NULL,
    especie TEXT NOT NULL,
    raca TEXT,
    idade_anos REAL,
    peso_kg REAL NOT NULL,
    condicoes TEXT NOT NULL DEFAULT '[]',
    medicacoes TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS consumo_diario (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pet_id TEXT NOT NULL REFERENCES pets(id),
    ml REAL NOT NULL,
    origem TEXT NOT NULL            -- semente (inicial) ou medido (sensor)
);

CREATE TABLE IF NOT EXISTS eventos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pet_id TEXT NOT NULL REFERENCES pets(id),
    ts REAL NOT NULL,
    tipo TEXT NOT NULL,             -- consumo ou reabastecimento
    ml REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS alertas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pet_id TEXT NOT NULL REFERENCES pets(id),
    ts REAL NOT NULL,
    status TEXT NOT NULL,
    gravidade TEXT NOT NULL,
    motivo TEXT NOT NULL,
    origem_analise TEXT NOT NULL,   -- llm ou padrao
    mensagem_tutor TEXT NOT NULL,
    resumo_clinica TEXT NOT NULL,
    payload TEXT NOT NULL           -- alerta completo em JSON
);

CREATE TABLE IF NOT EXISTS estado_atual (
    pet_id TEXT PRIMARY KEY REFERENCES pets(id),
    ts REAL NOT NULL,
    payload TEXT NOT NULL
);
"""

CAMPOS_PERFIL = ("idade_anos", "peso_kg", "condicoes", "medicacoes")


def _sem_casa_decimal(valor):
    # o banco devolve 9.0, mas para o texto o certo é 9
    if isinstance(valor, float) and valor.is_integer():
        return int(valor)
    return valor


def _perfil_de_linha(linha):
    perfil = dict(linha)
    perfil["idade_anos"] = _sem_casa_decimal(perfil["idade_anos"])
    perfil["peso_kg"] = _sem_casa_decimal(perfil["peso_kg"])
    perfil["condicoes"] = json.loads(perfil["condicoes"])
    perfil["medicacoes"] = json.loads(perfil["medicacoes"])
    return perfil


class Repositorio:
    def __init__(self, caminho=CAMINHO_PADRAO):
        self.con = sqlite3.connect(caminho, check_same_thread=False, timeout=10)
        self.con.row_factory = sqlite3.Row
        self.con.execute("PRAGMA journal_mode=WAL")
        self.con.executescript(ESQUEMA)

    def fechar(self):
        self.con.close()

    # perfis dos pets

    def semear_pets(self, caminho_json=JSON_PETS):
        # carrega os pets do pets.json só na primeira vez
        with open(caminho_json, encoding="utf-8") as f:
            pets = json.load(f)

        with self.con:
            for pet_id, p in pets.items():
                existe = self.con.execute("SELECT 1 FROM pets WHERE id = ?", (pet_id,)).fetchone()
                if existe:
                    continue
                self.con.execute(
                    "INSERT INTO pets (id, nome, especie, raca, idade_anos, peso_kg, condicoes, medicacoes) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (pet_id, p["nome"], p["especie"], p.get("raca"), p.get("idade_anos"),
                     p["peso_kg"], json.dumps(p.get("condicoes", []), ensure_ascii=False),
                     json.dumps(p.get("medicacoes", []), ensure_ascii=False)),
                )
                for ml in p.get("historico_dias_ml", []):
                    self.con.execute(
                        "INSERT INTO consumo_diario (pet_id, ml, origem) VALUES (?, ?, 'semente')",
                        (pet_id, ml),
                    )

    def listar_pets(self):
        linhas = self.con.execute("SELECT * FROM pets ORDER BY id").fetchall()
        return [_perfil_de_linha(l) for l in linhas]

    def perfil(self, pet_id):
        linha = self.con.execute("SELECT * FROM pets WHERE id = ?", (pet_id,)).fetchone()
        return _perfil_de_linha(linha) if linha else None

    def atualizar_perfil(self, pet_id, **campos):
        campos = {k: v for k, v in campos.items() if k in CAMPOS_PERFIL}
        if not campos:
            return
        for chave in ("condicoes", "medicacoes"):
            if chave in campos:
                campos[chave] = json.dumps(campos[chave], ensure_ascii=False)

        colunas = ", ".join(f"{k} = ?" for k in campos)
        with self.con:
            self.con.execute(
                f"UPDATE pets SET {colunas} WHERE id = ?", (*campos.values(), pet_id)
            )

    # consumo e eventos

    def historico(self, pet_id, limite=14):
        linhas = self.con.execute(
            "SELECT ml FROM consumo_diario WHERE pet_id = ? ORDER BY id DESC LIMIT ?",
            (pet_id, limite),
        ).fetchall()
        return [l["ml"] for l in reversed(linhas)]

    def salvar_dia(self, pet_id, ml):
        with self.con:
            self.con.execute(
                "INSERT INTO consumo_diario (pet_id, ml, origem) VALUES (?, ?, 'medido')",
                (pet_id, ml),
            )

    def salvar_evento(self, pet_id, ts, tipo, ml):
        with self.con:
            self.con.execute(
                "INSERT INTO eventos (pet_id, ts, tipo, ml) VALUES (?, ?, ?, ?)",
                (pet_id, ts, tipo, ml),
            )

    def eventos(self, pet_id, limite=50):
        linhas = self.con.execute(
            "SELECT id, ts, tipo, ml FROM eventos WHERE pet_id = ? ORDER BY id DESC LIMIT ?",
            (pet_id, limite),
        ).fetchall()
        return [dict(l) for l in linhas]

    # estado e alertas

    def salvar_estado(self, pet_id, ts, estado):
        with self.con:
            self.con.execute(
                "INSERT OR REPLACE INTO estado_atual (pet_id, ts, payload) VALUES (?, ?, ?)",
                (pet_id, ts, json.dumps(estado, ensure_ascii=False)),
            )

    def estado(self, pet_id):
        linha = self.con.execute(
            "SELECT payload FROM estado_atual WHERE pet_id = ?", (pet_id,)
        ).fetchone()
        return json.loads(linha["payload"]) if linha else None

    def salvar_alerta(self, pet_id, alerta):
        analise = alerta["analise"]
        with self.con:
            self.con.execute(
                "INSERT INTO alertas (pet_id, ts, status, gravidade, motivo, origem_analise, "
                "mensagem_tutor, resumo_clinica, payload) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (pet_id, alerta["ts"], alerta["status"], alerta["gravidade"], alerta["motivo"],
                 analise["origem"], analise["mensagem_tutor"], analise["resumo_clinica"],
                 json.dumps(alerta, ensure_ascii=False)),
            )

    def alertas(self, pet_id, limite=20):
        linhas = self.con.execute(
            "SELECT id, payload FROM alertas WHERE pet_id = ? ORDER BY id DESC LIMIT ?",
            (pet_id, limite),
        ).fetchall()
        return [{"id": l["id"], **json.loads(l["payload"])} for l in linhas]

    def total_alertas(self, pet_id):
        linha = self.con.execute(
            "SELECT COUNT(*) AS n FROM alertas WHERE pet_id = ?", (pet_id,)
        ).fetchone()
        return linha["n"]

    def reiniciar(self, pet_id):
        # apaga o que foi medido e mantém o perfil e o histórico inicial
        with self.con:
            self.con.execute("DELETE FROM eventos WHERE pet_id = ?", (pet_id,))
            self.con.execute("DELETE FROM alertas WHERE pet_id = ?", (pet_id,))
            self.con.execute("DELETE FROM estado_atual WHERE pet_id = ?", (pet_id,))
            self.con.execute(
                "DELETE FROM consumo_diario WHERE pet_id = ? AND origem = 'medido'", (pet_id,)
            )
