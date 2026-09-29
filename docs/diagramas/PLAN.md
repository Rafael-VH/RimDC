# Plan de diagramas

Estado: **0 de 5** diagramas del set canónico.

| # | Diagrama | Tipo | Estado | Pregunta que responde |
|---|----------|------|--------|----------------------|
| 1 | arquitectura | `architecture` | FALTA | ¿Cómo está partido el sistema y qué habla con qué? |
| 2 | pipeline | `workflow` | FALTA | ¿Qué le pasa a un dato desde que entra hasta que sale? |
| 3 | secuencia-clave | `sequence` | FALTA | ¿En qué orden se hablan los componentes en el caso más importante? |
| 4 | ciclo-de-vida | `lifecycle` | FALTA | ¿Qué estados atraviesa la entidad principal y cómo sale de cada uno? |
| 5 | datos *(opcional)* | `dataflow` | FALTA | ¿De dónde salen los datos, cómo se transforman y quién los consume? |

## Qué falta

### arquitectura — `architecture`

**Pregunta**: ¿Cómo está partido el sistema y qué habla con qué?

**Cuándo vale la pena**: Casi siempre. Si hay más de un módulo o capa, este es el diagrama base y el que se enlaza desde el README.

**Checklist de autoría**:

- [ ] Una frontera por capa o por límite real (no una por archivo)
- [ ] Entre 8 y 12 nodos; lo que no se usa a diario, a las tarjetas de resumen
- [ ] Cada nodo con sublabel concreto (tecnología o rol), no la repetición del título
- [ ] sources apuntando al archivo que define ese nodo: es la evidencia que audita archify-drift

### pipeline — `workflow`

**Pregunta**: ¿Qué le pasa a un dato desde que entra hasta que sale?

**Cuándo vale la pena**: Cuando el producto tiene una transformación central (entrada → proceso → salida) que conviene mostrar de punta a punta.

**Checklist de autoría**:

- [ ] Un solo camino principal evidente, de izquierda a derecha
- [ ] Las ramas laterales salen del nodo del camino más cercano
- [ ] Etiquetas en las aristas con la acción concreta, no con el nombre de los nodos
- [ ] Los puntos de fallo o reintento, si existen, como variante diferenciada

### secuencia-clave — `sequence`

**Pregunta**: ¿En qué orden se hablan los componentes en el caso más importante?

**Cuándo vale la pena**: Cuando hay una llamada encadenada entre servicios, o un arranque/descarga con pasos y retornos que no se entiende leyendo el código.

**Checklist de autoría**:

- [ ] Participantes semánticos (servicio, store, externo), no clases
- [ ] Ida y vuelta: marcar los retornos con su variante
- [ ] Agrupar en segmentos si la secuencia tiene fases claras
- [ ] Nombrar el caso concreto que se está contando (no 'flujo general')

### ciclo-de-vida — `lifecycle`

**Pregunta**: ¿Qué estados atraviesa la entidad principal y cómo sale de cada uno?

**Cuándo vale la pena**: Cuando hay una entidad con estados, esperas o reintentos: un job, un pedido, un audio pendiente, una sesión.

**Checklist de autoría**:

- [ ] Estados con nombre del dominio, no genéricos ('procesando', no 'estado 2')
- [ ] Distinguir los finales de las esperas recuperables
- [ ] Un fallo recuperable necesita su transición real de vuelta al estado activo
- [ ] Marcar el estado inicial y los terminales

### datos — `dataflow` (opcional)

**Pregunta**: ¿De dónde salen los datos, cómo se transforman y quién los consume?

**Cuándo vale la pena**: Sólo si hay un pipeline de datos real (ETL, eventos, linaje). En una app sin ingestión, no aporta.

**Checklist de autoría**:

- [ ] Una etapa por subgrafo, en orden de recorrido
- [ ] Nombrar los contratos o esquemas que cruzan cada salto
- [ ] Separar el camino feliz del de error o descarte
- [ ] Marcar quién es dueño de cada consumidor

## Contexto del repo

- Archivos relevados (hasta 3 niveles): 8
- Extensiones más frecuentes: .md (2), .xml (1), .py (1), .txt (1), .csproj (1), .cs (1)
- Módulos de primer nivel: About, bot

---

Generado por la skill `archify-suite`. La autoría de cada diagrama es de `/archify`;
este plan define el estándar y mide el avance.
