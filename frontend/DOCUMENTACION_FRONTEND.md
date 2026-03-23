# Frontend MatProp-ML

## 1. Nombre del servicio
Frontend MatProp-ML (Next.js App Router)

## 2. Descripcion
Aplicacion web cliente que expone una interfaz conversacional para consultar el stack de modelos de materiales. Implementa un layout principal con chat y panel lateral, y paginas utilitarias para validar el estado del backend.

## 3. Responsabilidad dentro del sistema
- Proveer la experiencia de chat al usuario final.
- Enviar prompts al backend de completions mediante HTTP.
- Exponer paginas de salud y mantenimiento para endpoints del backend.

## 4. Dependencias
### 4.1 Internas
- Backend de completions configurado via `NEXT_PUBLIC_API_URL` (por defecto apunta a `/v1/completions`).

### 4.2 Externas
- Next.js 14, React 18, TypeScript 5.
- Navegador moderno con soporte de Fetch API.

## 5. Requisitos del entorno
- Runtime: Node.js 18+ para desarrollo, Node.js 20 en la imagen Docker.
- Variables de entorno requeridas: `NEXT_PUBLIC_API_URL` (base del backend). `INTERNAL_API_URL` se acepta en Dockerfile pero no se usa en el codigo cliente.
- Puerto expuesto: 3000.
- Requisitos de hardware: No aplica.
- Requisitos de red: acceso HTTP al backend configurado.

## 6. Estructura de carpetas (vision general)
- `package.json`: scripts y dependencias.
- `Dockerfile`: build y runtime multistage.
- `src/env.client.ts`: exporta variables de entorno a cliente.
- `src/app/`: App Router de Next.js.
  - `components/`: componentes de UI.
  - `clear/`, `history/`, `test/`, `configuration/`: paginas utilitarias.

## 7. Descripcion detallada de archivos

### 7.1 package.json
- Rol del archivo: scripts de build/run y dependencias.
- Funciones publicas: No aplica.

### 7.2 Dockerfile
- Rol del archivo: build multistage (builder + runner) para Next.js.
- Funciones publicas: No aplica.

### 7.3 src/env.client.ts
- Rol del archivo: expone `ENV.API_URL` desde `NEXT_PUBLIC_API_URL`.
- Funciones publicas: No aplica.

### 7.4 src/app/layout.tsx
- Rol del archivo: layout raiz y metadatos HTML.
- Funciones publicas: No aplica.

### 7.5 src/app/globals.css
- Rol del archivo: estilos globales base (reset, tipografia, fondo).
- Funciones publicas: No aplica.

### 7.6 src/app/page.tsx
- Rol del archivo: pagina principal con el layout de chat y sidebar.
- Funciones publicas: No aplica.

### 7.7 src/app/components/ChatWindow.tsx
- Rol del archivo: estado de mensajes, llamada a completions y render del chat.
- Funciones publicas: No aplica.

### 7.8 src/app/components/ChatMessage.tsx
- Rol del archivo: render de un mensaje individual segun remitente.
- Funciones publicas: No aplica.

### 7.9 src/app/components/ChatInput.tsx
- Rol del archivo: input controlado y envio de mensajes.
- Funciones publicas: No aplica.

### 7.10 src/app/components/Sidebar.tsx
- Rol del archivo: panel informativo con toggle y link de configuracion.
- Funciones publicas: No aplica.

### 7.11 src/app/clear/page.tsx
- Rol del archivo: pagina utilitaria que llama `/v1/clear_history`.
- Funciones publicas: No aplica.

### 7.12 src/app/history/page.tsx
- Rol del archivo: pagina utilitaria que llama `/v1/conversation_history`.
- Funciones publicas: No aplica.

### 7.13 src/app/test/page.tsx
- Rol del archivo: pagina utilitaria que llama `/v1/health`.
- Funciones publicas: No aplica.

### 7.14 src/app/configuration/page.tsx
- Rol del archivo: placeholder visual para configuracion.
- Funciones publicas: No aplica.

## 8. Modelos de datos utilizados
- `Message`: `{ text: string, sender: "user" | "agent" | "system" }`.
- Respuesta de completions: `{ choices: [{ text: string }], ... }`.

## 9. API endpoints (si aplica)
No aplica.

## 10. Flujo de trabajo
1) El usuario escribe un prompt en `ChatInput`.
2) `ChatWindow` agrega el mensaje, llama a `/v1/completions` y renderiza la respuesta.
3) Las paginas utilitarias hacen `fetch` a `clear_history`, `conversation_history` y `health`.

## 11. Diagrama textual del flujo (opcional)
Usuario -> ChatInput -> ChatWindow -> Backend /v1/completions -> UI

## 12. Consideraciones tecnicas / decisiones de diseno
- Todo el frontend es client-side; depende de `NEXT_PUBLIC_API_URL`.
- El endpoint se normaliza removiendo barras finales para evitar dobles slashes.
- No existe manejo de autenticacion ni timeouts custom.

## 13. Operacion y despliegue (si aplica)
- Desarrollo: `npm run dev`.
- Produccion: `npm run build` y `npm run start`.
- Docker: build multistage con `NEXT_PUBLIC_API_URL` en build y runtime.

## 14. Observabilidad y soporte (si aplica)
No aplica.

## 15. Actualizacion de arquitectura (2026-03-15)
- Entorno cliente:
  - El frontend usa `ENV.API_URL` desde `src/env.client.ts` como unica fuente de configuracion.
  - Se elimino el acceso directo a `process.env` en paginas utilitarias (`clear`, `history`, `test`).
  - `NEXT_PUBLIC_API_URL` es obligatorio; si falta, el build/runtime falla de forma explicita.
- Migracion de `clear_history`:
  - `clear/page.tsx` invoca primero `POST /v1/clear_history`.
  - Se mantiene fallback temporal a `GET /v1/clear_history` durante la ventana de deprecacion (1 release).
- Rendimiento de chat:
  - Se reemplazo render caracter-a-caracter por actualizacion en chunks temporizados para reducir re-renders en respuestas largas.

## 16. Actualizacion de arquitectura (2026-03-18)
- Selector de modo en el input:
  - Se agrego un boton `+` sin fondo integrado a la izquierda del campo de mensaje.
  - El boton abre un popover con una unica opcion: `More context`.
  - `More context` se implementa como toggle ON/OFF y persiste durante toda la sesion del chat (no se reinicia por mensaje).
- Enrutamiento condicional de completions:
  - Si `More context` esta OFF, el frontend llama a `/v1/completions` (chat simple).
  - Si `More context` esta ON, el frontend llama a `/v2/completions` (agente completo).
  - La base del backend sigue resolviendose con `NEXT_PUBLIC_API_URL` y normalizacion de slash final.
- UX y accesibilidad:
  - Estado visual seleccionado para `More context` con efecto de hundido, opacidad atenuada y borde blanco tenue.
  - Cierre del popover por click fuera, tecla Escape y seleccion del toggle.
  - Atributos ARIA de control (`aria-expanded`, `aria-controls`, `menuitemcheckbox`).
- Componentes impactados:
  - `src/app/components/ChatInput.tsx` (boton +, popover, toggle).
  - `src/app/components/ChatWindow.tsx` (estado persistente del modo y seleccion de endpoint v1/v2).
