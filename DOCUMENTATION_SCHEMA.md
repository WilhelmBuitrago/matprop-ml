# Esquema maestro de documentacion de servicios

Este documento define el esquema obligatorio y estandarizado que debe seguir toda documentacion tecnica de servicios del proyecto. Todas las secciones son obligatorias. Si una seccion no aplica, se debe indicar explicitamente: "No aplica.".

## 1. Nombre del servicio
- Nombre oficial del servicio.
- Identificador corto usado en despliegue (si aplica).

## 2. Descripcion
- Resumen tecnico conciso del servicio y su proposito.
- Alcance funcional y limites principales.

## 3. Responsabilidad dentro del sistema
- Rol del servicio en la arquitectura global.
- Interacciones de alto nivel con otros servicios.

## 4. Dependencias
### 4.1 Internas
- Servicios del proyecto requeridos (nombre, proposito de la dependencia, endpoint/puerto si aplica).

### 4.2 Externas
- Librerias, servicios SaaS, APIs de terceros y recursos externos criticos.

## 5. Requisitos del entorno
- Runtime (lenguaje, version minima).
- Variables de entorno requeridas.
- Puertos expuestos.
- Requisitos de hardware (CPU/GPU/RAM) si aplica.
- Requisitos de red (salidas a internet, dominios, etc.) si aplica.

## 6. Estructura de carpetas (vision general)
- Descripcion de carpetas principales y proposito.

## 7. Descripcion detallada de archivos
- Listar archivos relevantes con su responsabilidad.
- Para archivos Python, incluir seccion de funciones publicas con el siguiente formato minimo:

### 7.x path/del/archivo.py
- Rol del archivo.
- Funciones publicas:
	- Firma: `nombre_funcion(parametro: tipo, ...) -> tipo`
	- Inputs: lista de parametros con tipo y significado.
	- Outputs: tipo y significado.
	- Efectos secundarios: IO, red, cache, disco, etc.
	- Excepciones: errores relevantes y condiciones.
	- Restricciones: limites, supuestos, formatos esperados.

Si el archivo no es Python, indicar "No aplica." en la seccion de funciones publicas.

## 8. Modelos de datos utilizados
- Modelos Pydantic, dataclasses, esquemas JSON u otros contratos.
- Campos relevantes y semantica.

## 9. API endpoints (si aplica)
- Endpoint, metodo, request body, response body y codigos relevantes.

## 10. Flujo de trabajo
- Pasos secuenciales principales (desde request hasta respuesta).

## 11. Diagrama textual del flujo (opcional)
- Diagrama textual simple (ASCII) que represente el flujo.

## 12. Consideraciones tecnicas / decisiones de diseno
- Decisiones clave, trade-offs, restricciones o riesgos conocidos.

## 13. Operacion y despliegue (si aplica)
- Como ejecutar localmente y en contenedores.
- Dependencias de arranque y orden recomendado.

## 14. Observabilidad y soporte (si aplica)
- Logs, metricas, healthchecks, diagnosticos.
