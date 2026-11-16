#!/usr/bin/env python
"""
Sistema de validación para el índice RAG.

Verifica que el índice está en buen estado y cubre todos los documentos.
Útil para ejecutar después de rebuild o agregar documentos.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, '.')

from app import config
from app.models.rag import service

def validate_index():
    """Valida que el índice esté completo y correcto."""
    
    print("=" * 80)
    print("VALIDACION DEL INDICE RAG")
    print("=" * 80)
    print()
    
    errors = []
    warnings = []
    
    # 1. Verificar que el índice existe
    print("1. Verificando existencia del índice...")
    try:
        status = service.index_status()
        indexed_chunks = status['indexed_chunks']
        is_ready = status['ready']
        
        print(f"   Chunks indexados: {indexed_chunks}")
        print(f"   Estado ready: {is_ready}")
        
        if not is_ready:
            errors.append("El índice no está listo (ready=False)")
        if indexed_chunks == 0:
            errors.append("El índice está vacío (0 chunks)")
    except Exception as e:
        errors.append(f"Error al verificar estado: {e}")
        return errors, warnings
    
    print()
    
    # 2. Verificar cobertura de documentos
    print("2. Verificando cobertura de documentos...")
    
    try:
        # Documentos en disk
        data_dir = config.RAG_DATA_DIR
        disk_files = set()
        for f in os.listdir(data_dir):
            if f.lower().endswith(('.txt', '.json', '.jsonl')):
                disk_files.add(f)
        
        print(f"   Archivos en disk: {len(disk_files)}")
        
        # Documentos en índice
        import chromadb
        client = chromadb.PersistentClient(path=config.RAG_DB_DIR)
        collection = client.get_collection("arte")
        results = collection.get(limit=None)
        
        indexed_files = set()
        if results and results['metadatas']:
            for meta in results['metadatas']:
                if 'filename' in meta:
                    # Extraer nombre del archivo del path relativo
                    fn = Path(meta['filename']).name
                    indexed_files.add(fn)
        
        print(f"   Archivos en índice: {len(indexed_files)}")
        
        # Verificar cobertura
        missing = disk_files - indexed_files
        extra = indexed_files - disk_files
        
        if missing:
            msg = f"Archivos NO indexados: {missing}"
            print(f"   FALTA: {len(missing)} archivo(s)")
            errors.append(msg)
            for f in sorted(missing):
                print(f"      - {f}")
        
        if extra:
            msg = f"Archivos extra en índice: {extra}"
            print(f"   EXTRA: {len(extra)} archivo(s)")
            warnings.append(msg)
            for f in sorted(extra):
                print(f"      - {f}")
        
        if not missing and not extra:
            print("   Cobertura: PERFECTA")
    
    except Exception as e:
        errors.append(f"Error al verificar cobertura: {e}")
    
    print()
    
    # 3. Verificar recuperación de cubismo y barroco
    print("3. Verificando recuperación de temas...")
    
    try:
        test_q_cubismo = "¿Qué es el cubismo?"
        test_q_barroco = "¿Qué es el barroco?"
        
        hits_cubismo = service.retrieve(test_q_cubismo, k=10)
        hits_barroco = service.retrieve(test_q_barroco, k=10)
        
        cubismo_files = {Path(h.get('filename', '')).name for h in hits_cubismo}
        barroco_files = {Path(h.get('filename', '')).name for h in hits_barroco}
        
        print(f"   Cubismo - Documentos recuperados: {len(cubismo_files)}")
        print(f"   Barroco - Documentos recuperados: {len(barroco_files)}")
        
        if len(cubismo_files) < 3:
            warnings.append(f"Retrieval de cubismo bajo: {len(cubismo_files)} archivos")
        if len(barroco_files) < 3:
            warnings.append(f"Retrieval de barroco bajo: {len(barroco_files)} archivos")
    
    except Exception as e:
        errors.append(f"Error al verificar retrieval: {e}")
    
    print()
    
    # 4. Resumen
    print("=" * 80)
    print("RESUMEN")
    print("=" * 80)
    
    if not errors and not warnings:
        print("✓ Indice está en buen estado")
        return errors, warnings
    
    if errors:
        print(f"\nERRORES ({len(errors)}):")
        for i, e in enumerate(errors, 1):
            print(f"  {i}. {e}")
    
    if warnings:
        print(f"\nADVERTENCIAS ({len(warnings)}):")
        for i, w in enumerate(warnings, 1):
            print(f"  {i}. {w}")
    
    return errors, warnings

if __name__ == "__main__":
    errors, warnings = validate_index()
    
    sys.exit(1 if errors else 0)
