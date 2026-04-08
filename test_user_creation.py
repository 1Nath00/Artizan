"""
Script para probar la creación de usuarios con diferentes contraseñas
"""
from app.middleware import logger

def test_password_validation():
    """Prueba la validación de contraseñas"""
    from app.auth.schemas import UserCreate
    from pydantic import ValidationError
    
    logger.info("=== TEST: Validación de contraseñas ===\n")
    
    # Test 1: Contraseña válida corta
    logger.info("Test 1: Contraseña válida corta")
    try:
        user = UserCreate(username="testuser", email="test@example.com", password="1234")
        logger.info(f"✓ Contraseña válida: {len(user.password)} caracteres")
    except ValidationError as e:
        logger.error(f"✗ Error de validación: {e}")
    
    # Test 2: Contraseña válida larga
    logger.info("\nTest 2: Contraseña válida larga (60 chars)")
    try:
        long_password = "a" * 60
        user = UserCreate(username="testuser2", email="test2@example.com", password=long_password)
        logger.info(f"✓ Contraseña válida: {len(user.password)} caracteres, {len(user.password.encode('utf-8'))} bytes")
    except ValidationError as e:
        logger.error(f"✗ Error de validación: {e}")
    
    # Test 3: Contraseña demasiado corta
    logger.info("\nTest 3: Contraseña demasiado corta")
    try:
        user = UserCreate(username="testuser3", email="test3@example.com", password="123")
        logger.error("✗ Debería haber fallado pero pasó")
    except ValidationError as e:
        logger.info(f"✓ Validación correcta: {e.errors()[0]['msg']}")
    
    # Test 4: Contraseña demasiado larga (>72 bytes)
    logger.info("\nTest 4: Contraseña demasiado larga (>72 bytes)")
    try:
        # Crear una contraseña de más de 72 bytes
        too_long = "a" * 73
        user = UserCreate(username="testuser4", email="test4@example.com", password=too_long)
        logger.error("✗ Debería haber fallado pero pasó")
    except ValidationError as e:
        logger.info(f"✓ Validación correcta: {e.errors()[0]['msg']}")
    
    # Test 5: Contraseña vacía
    logger.info("\nTest 5: Contraseña vacía")
    try:
        user = UserCreate(username="testuser5", email="test5@example.com", password="")
        logger.error("✗ Debería haber fallado pero pasó")
    except ValidationError as e:
        logger.info(f"✓ Validación correcta: {e.errors()[0]['msg']}")
    
    logger.info("\n=== FIN TEST: Validación de contraseñas ===\n")


def test_hash_generation():
    """Prueba la generación de hashes"""
    from app.auth.service import get_password_hash, verify_password
    
    logger.info("=== TEST: Generación de hashes ===\n")
    
    # Test 1: Hash simple
    logger.info("Test 1: Generación de hash simple")
    password = "test1234"
    try:
        hash_result = get_password_hash(password)
        logger.info(f"✓ Hash generado: {hash_result[:20]}... (longitud: {len(hash_result)})")
        
        # Verificar que el hash funcione
        if verify_password(password, hash_result):
            logger.info("✓ Verificación de hash correcta")
        else:
            logger.error("✗ Verificación de hash falló")
    except Exception as e:
        logger.error(f"✗ Error: {e}", exc_info=True)
    
    # Test 2: Hash con contraseña larga
    logger.info("\nTest 2: Hash con contraseña de 70 caracteres")
    long_password = "a" * 70
    try:
        hash_result = get_password_hash(long_password)
        logger.info(f"✓ Hash generado: {hash_result[:20]}... (longitud: {len(hash_result)})")
        
        if verify_password(long_password, hash_result):
            logger.info("✓ Verificación de hash correcta")
        else:
            logger.error("✗ Verificación de hash falló")
    except Exception as e:
        logger.error(f"✗ Error: {e}", exc_info=True)
    
    logger.info("\n=== FIN TEST: Generación de hashes ===\n")


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("INICIANDO PRUEBAS DE CREACIÓN DE USUARIOS")
    logger.info("=" * 60 + "\n")
    
    test_password_validation()
    test_hash_generation()
    
    logger.info("=" * 60)
    logger.info("PRUEBAS COMPLETADAS")
    logger.info("=" * 60)
