{{- define "quillo.labels" -}}
app.kubernetes.io/name: quillo
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version }}
{{- end -}}

{{- define "quillo.selector" -}}
app.kubernetes.io/name: quillo
app.kubernetes.io/instance: {{ .root.Release.Name }}
app.kubernetes.io/component: {{ .component }}
{{- end -}}

{{/* Ảnh: (list $ repository tag). Có image.registry thì bỏ host gốc (phần đầu có "." hoặc ":") rồi thêm registry. */}}
{{- define "quillo.image" -}}
{{- $root := index . 0 -}}
{{- $repository := index . 1 -}}
{{- $tag := index . 2 | default $root.Chart.AppVersion -}}
{{- with $root.Values.image.registry -}}
{{- $parts := splitList "/" $repository -}}
{{- if and (gt (len $parts) 1) (or (contains "." (first $parts)) (contains ":" (first $parts))) -}}
{{- $repository = join "/" (rest $parts) -}}
{{- end -}}
{{- printf "%s/%s:%s" . $repository $tag -}}
{{- else -}}
{{- printf "%s:%s" $repository $tag -}}
{{- end -}}
{{- end -}}

{{- define "quillo.authSecret" -}}
{{- .Values.auth.existingSecret | default (printf "%s-auth" .Release.Name) -}}
{{- end -}}

{{/* securityContext của pod: (dict "root" $ "component" "api"); giá trị riêng của thành phần đè giá trị chung. */}}
{{- define "quillo.podSecurityContext" -}}
{{- $own := (index .root.Values .component).podSecurityContext | default dict -}}
{{- with merge (deepCopy $own) (deepCopy .root.Values.podSecurityContext) }}
securityContext:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- end -}}

{{/* securityContext + resources của một container: (dict "root" $ "component" "llm" "resources" "models"). */}}
{{- define "quillo.containerExtras" -}}
{{- $own := (index .root.Values .component).containerSecurityContext | default dict -}}
{{- with merge (deepCopy $own) (deepCopy .root.Values.containerSecurityContext) }}
securityContext:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- with index .root.Values.resources (.resources | default .component) }}
resources:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- end -}}

{{- define "quillo.pullSecrets" -}}
{{- with .Values.image.pullSecrets }}
imagePullSecrets:
  {{- toYaml . | nindent 2 }}
{{- end }}
{{- end -}}

{{- define "quillo.appEnv" -}}
- name: QUILLO_DB_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ include "quillo.authSecret" . }}
      key: db-password
- name: QUILLO_DATABASE_URL
  value: "postgresql://quillo:$(QUILLO_DB_PASSWORD)@{{ .Release.Name }}-db:5432/quillo"
- name: QUILLO_ADMIN_TOKEN
  valueFrom:
    secretKeyRef:
      name: {{ include "quillo.authSecret" . }}
      key: admin-token
- name: QUILLO_LLM_URL
  value: "http://{{ .Release.Name }}-llm:8080"
- name: QUILLO_EMBED_URL
  value: "http://{{ .Release.Name }}-embed:8080"
- name: QUILLO_MAX_UPLOAD_MB
  value: {{ .Values.maxUploadMb | quote }}
- name: QUILLO_LOG_LEVEL
  value: {{ .Values.logLevel | quote }}
{{- end -}}
