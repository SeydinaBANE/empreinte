{{- define "empreinte.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "empreinte.fullname" -}}
{{- printf "%s-%s" .Release.Name (include "empreinte.name" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "empreinte.labels" -}}
app.kubernetes.io/name: {{ include "empreinte.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "empreinte.selectorLabels" -}}
app.kubernetes.io/name: {{ include "empreinte.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "empreinte.image" -}}
{{- printf "%s:%s" .Values.image.repository (.Values.image.tag | default .Chart.AppVersion) -}}
{{- end -}}
