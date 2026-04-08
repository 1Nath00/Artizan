"""
Script para debugear el problema del hash de contraseñas
"""
from app.auth.service import get_password_hash, pwd_context
from app.middleware import logger

def test_hash_generation():
    """Prueba la generación de hashes"""
    logger.info("=== INICIO TEST HASH ===")
    
    # Prueba 1: Hash directo con pwd_context
    test_password = "test123"
    logger.info(f"Probando con contraseña: {test_password}")
    
    try:
        # Método 1: Usando pwd_context directamente
        logger.info("Método 1: pwd_context.hash() directamente")
        hash1 = pwd_context.hash(test_password)
        logger.info(f"Hash generado (método 1): {hash1}")
        logger.info(f"Tipo de hash: {type(hash1)}")
        logger.info(f"Longitud del hash: {len(hash1)}")
        
        # Método 2: Usando la función get_password_hash
        logger.info("\nMétodo 2: get_password_hash()")
        hash2 = get_password_hash(test_password)
        logger.info(f"Hash generado (método 2): {hash2}")
        logger.info(f"Tipo de hash: {type(hash2)}")
        logger.info(f"Longitud del hash: {len(hash2)}")
        
        # Verificar que el hash funciona
        logger.info("\nVerificando hash...")
        is_valid = pwd_context.verify(test_password, hash2)
        logger.info(f"¿Hash válido?: {is_valid}")
        
    except Exception as e:
        logger.error(f"ERROR durante generación de hash: {e}", exc_info=True)
    
    logger.info("=== FIN TEST HASH ===")

if __name__ == "__main__":
    test_hash_generation()
