{{- define "olist-shop.name" -}}
{{- .Chart.Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "olist-shop.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "olist-shop.selectorLabels" -}}
app.kubernetes.io/name: {{ include "olist-shop.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "olist-shop.labels" -}}
helm.sh/chart: {{ include "olist-shop.chart" . }}
{{ include "olist-shop.selectorLabels" . }}
app.kubernetes.io/version: {{ include "olist-shop.version" . | quote }}
app.kubernetes.io/part-of: olist-shop
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "olist-shop.version" -}}
{{- .Values.image.tag | default .Chart.AppVersion }}
{{- end }}

{{- define "olist-shop.image" -}}
{{- printf "%s:%s" .Values.image.repository (include "olist-shop.version" .) }}
{{- end }}

{{- define "olist-shop.podSecurity" -}}
runAsNonRoot: true
seccompProfile:
  type: RuntimeDefault
{{- end }}

{{- define "olist-shop.containerSecurity" -}}
allowPrivilegeEscalation: false
readOnlyRootFilesystem: true
capabilities:
  drop: ["ALL"]
{{- end }}

{{- define "olist-shop.dnsEgress" -}}
- to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
  ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
{{- end }}

{{- define "olist-shop.dataEgress" -}}
- to:
    - podSelector:
        matchLabels:
          {{- toYaml .Values.networkPolicy.database.podLabels | nindent 10 }}
  ports:
    - protocol: TCP
      port: {{ .Values.networkPolicy.database.port }}
- to:
    - podSelector:
        matchLabels:
          {{- toYaml .Values.networkPolicy.redis.podLabels | nindent 10 }}
  ports:
    - protocol: TCP
      port: {{ .Values.networkPolicy.redis.port }}
{{- end }}
