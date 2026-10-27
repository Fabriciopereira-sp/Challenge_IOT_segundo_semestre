from pathlib import Path
from typing import List, Optional

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from db import CAMINHO_PADRAO, Repositorio


class PerfilIn(BaseModel):
    idade_anos: Optional[float] = Field(default=None, gt=0)
    peso_kg: Optional[float] = Field(default=None, gt=0)
    condicoes: Optional[List[str]] = None
    medicacoes: Optional[List[str]] = None


def criar_app(caminho_db=CAMINHO_PADRAO):
    app = FastAPI(
        title="CLYVO VET - API do Bebedouro Inteligente",
        description="Consumo de água, alertas da IA e perfil dos pets.",
        version="1.0",
    )

    repo_inicial = Repositorio(caminho_db)
    repo_inicial.semear_pets()
    repo_inicial.fechar()

    def obter_repo():
        repo = Repositorio(caminho_db)
        try:
            yield repo
        finally:
            repo.fechar()

    def pet_ou_404(repo, pet_id):
        perfil = repo.perfil(pet_id)
        if perfil is None:
            raise HTTPException(status_code=404, detail="Pet não encontrado")
        return perfil

    @app.get("/", include_in_schema=False)
    def inicio():
        pagina = Path(__file__).with_name("dashboard.html")
        if pagina.exists():
            return FileResponse(pagina)
        return {"mensagem": "API no ar. A documentação está em /docs"}

    @app.get("/saude")
    def saude():
        return {"status": "ok"}

    @app.get("/pets")
    def listar_pets(repo: Repositorio = Depends(obter_repo)):
        return repo.listar_pets()

    @app.get("/pets/{pet_id}")
    def perfil_do_pet(pet_id: str, repo: Repositorio = Depends(obter_repo)):
        return pet_ou_404(repo, pet_id)

    @app.put("/pets/{pet_id}/perfil")
    def atualizar_perfil(pet_id: str, dados: PerfilIn, repo: Repositorio = Depends(obter_repo)):
        pet_ou_404(repo, pet_id)
        repo.atualizar_perfil(pet_id, **dados.model_dump(exclude_none=True))
        return repo.perfil(pet_id)

    @app.get("/pets/{pet_id}/estado")
    def estado_atual(pet_id: str, repo: Repositorio = Depends(obter_repo)):
        pet_ou_404(repo, pet_id)
        estado = repo.estado(pet_id)
        if estado is None:
            raise HTTPException(status_code=404, detail="Ainda não há leituras para este pet")
        return estado

    @app.get("/pets/{pet_id}/alertas")
    def alertas(pet_id: str, limite: int = Query(20, ge=1, le=100),
                repo: Repositorio = Depends(obter_repo)):
        pet_ou_404(repo, pet_id)
        return repo.alertas(pet_id, limite)

    @app.get("/pets/{pet_id}/consumo")
    def consumo(pet_id: str, repo: Repositorio = Depends(obter_repo)):
        pet_ou_404(repo, pet_id)
        return {"historico_dias_ml": repo.historico(pet_id)}

    @app.get("/pets/{pet_id}/eventos")
    def eventos(pet_id: str, limite: int = Query(50, ge=1, le=500),
                repo: Repositorio = Depends(obter_repo)):
        pet_ou_404(repo, pet_id)
        return repo.eventos(pet_id, limite)

    @app.get("/pets/{pet_id}/resumo-clinica")
    def resumo_clinica(pet_id: str, repo: Repositorio = Depends(obter_repo)):
        perfil = pet_ou_404(repo, pet_id)
        ultimos = repo.alertas(pet_id, 1)
        return {
            "perfil": perfil,
            "estado": repo.estado(pet_id),
            "historico_dias_ml": repo.historico(pet_id),
            "total_alertas": repo.total_alertas(pet_id),
            "ultimo_alerta": ultimos[0] if ultimos else None,
        }

    return app


if __name__ == "__main__":
    uvicorn.run(criar_app(), host="127.0.0.1", port=8000)
