from __future__ import annotations

from typing import Any

from database.db import get_connection, init_db


def save_scan(scan: dict[str, Any], motoristas: list[dict[str, Any]], decisao: dict[str, Any]) -> int:
    init_db()
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO scans (
                created_at, arquivo_nome, link_busca, origem, destino,
                data_viagem, sentido, status_validacao, observacoes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                scan.get("created_at"),
                scan.get("arquivo_nome"),
                scan.get("link_busca"),
                scan.get("origem"),
                scan.get("destino"),
                scan.get("data_viagem"),
                scan.get("sentido"),
                scan.get("status_validacao"),
                scan.get("observacoes"),
            ),
        )
        scan_id = int(cur.lastrowid)

        for motorista in motoristas:
            conn.execute(
                """
                INSERT INTO motoristas (
                    scan_id, nome_motorista, horario, preco, vagas, status,
                    eh_ezequiel, eh_barbosa, contexto
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    scan_id,
                    motorista.get("nome_motorista"),
                    motorista.get("horario"),
                    motorista.get("preco"),
                    motorista.get("vagas"),
                    motorista.get("status"),
                    1 if motorista.get("eh_ezequiel") else 0,
                    1 if motorista.get("eh_barbosa") else 0,
                    motorista.get("contexto"),
                ),
            )

        conn.execute(
            """
            INSERT INTO decisoes (
                scan_id, acao, conta, origem, destino_final, intermediarias,
                data, horario, preco_sugerido, risco_conflito,
                status_validacao, motivo
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                scan_id,
                decisao.get("acao"),
                decisao.get("conta"),
                decisao.get("origem"),
                decisao.get("destino_final"),
                decisao.get("intermediarias"),
                decisao.get("data"),
                decisao.get("horario"),
                decisao.get("preco_sugerido"),
                decisao.get("risco_conflito"),
                decisao.get("status_validacao"),
                decisao.get("motivo"),
            ),
        )
        conn.commit()
        return scan_id


def list_recent_scans(limit: int = 50) -> list[dict[str, Any]]:
    init_db()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                s.id,
                s.created_at,
                s.arquivo_nome,
                s.link_busca,
                s.origem,
                s.destino,
                s.data_viagem,
                s.sentido,
                s.status_validacao,
                d.acao,
                d.conta,
                d.horario,
                d.preco_sugerido,
                d.risco_conflito
            FROM scans s
            LEFT JOIN decisoes d ON d.scan_id = s.id
            ORDER BY s.id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]
