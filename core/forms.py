from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User, Municipio, Cliente, Video, Playlist, DispositivoTV, AgendamentoExibicao, Segmento, AppVersion, ConteudoCorporativo, ConfiguracaoAPI


class CustomUserCreationForm(UserCreationForm):
    """Formulário para criação de usuários customizados"""

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'role')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'


class CustomUserChangeForm(UserChangeForm):
    """Formulário para alteração de usuários customizados"""

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'role')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'


class MunicipioForm(forms.ModelForm):
    """Formulário para municípios"""

    class Meta:
        model = Municipio
        fields = ['nome', 'estado', 'franqueado', 'latitude', 'longitude']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do município'}),
            'estado': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Estado (UF)'}),
            'franqueado': forms.Select(attrs={'class': 'form-select'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ex: -23.550520', 'step': '0.000001'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ex: -46.633308', 'step': '0.000001'}),
        }


class SegmentoForm(forms.ModelForm):
    """Formulário para segmentos"""

    class Meta:
        model = Segmento
        fields = ['nome', 'descricao', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do segmento'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descrição do segmento'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ClienteForm(forms.ModelForm):
    """Formulário para clientes"""

    class Meta:
        model = Cliente
        fields = ['user', 'empresa', 'segmento', 'municipios', 'franqueado', 'ativo', 'observacoes']
        widgets = {
            'user': forms.Select(attrs={'class': 'form-select'}),
            'empresa': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome da empresa'}),
            'segmento': forms.Select(attrs={'class': 'form-select'}),
            'municipios': forms.SelectMultiple(attrs={'class': 'form-select', 'size': '5'}),
            'franqueado': forms.Select(attrs={'class': 'form-select'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Observações sobre o cliente'}),
        }

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            if user.role == 'FRANCHISEE':
                # Franqueados só podem criar clientes para seus municípios
                municipios = Municipio.objects.filter(franqueado=user)
                self.fields['municipios'].queryset = municipios
                # Franqueado é definido automaticamente
                self.fields['franqueado'].initial = user
                self.fields['franqueado'].widget = forms.HiddenInput()
            elif user.role == 'OWNER':
                # Owners podem escolher qualquer franqueado
                self.fields['franqueado'].queryset = User.objects.filter(role='FRANCHISEE', is_active=True)

            # Filtrar usuários que ainda não são clientes
            existing_clients = Cliente.objects.values_list('user', flat=True)
            self.fields['user'].queryset = User.objects.filter(
                role='CLIENT',
                is_active=True
            ).exclude(id__in=existing_clients)
    
    def clean(self):
        cleaned_data = super().clean()
        segmento = cleaned_data.get('segmento')
        municipios = cleaned_data.get('municipios')
        
        if segmento and municipios:
            # Verificar se já existe cliente no mesmo segmento em algum dos municípios
            for municipio in municipios:
                existe = Cliente.objects.filter(
                    segmento=segmento,
                    municipios=municipio
                )
                
                # Se estiver editando, excluir o próprio cliente da verificação
                if self.instance.pk:
                    existe = existe.exclude(pk=self.instance.pk)
                
                if existe.exists():
                    cliente_existente = existe.first()
                    raise forms.ValidationError(
                        f'Já existe um cliente no segmento "{cliente_existente.get_segmento_display()}" '
                        f'no município {municipio.nome}/{municipio.estado}: {cliente_existente.empresa}. '
                        f'Regra: apenas uma marca por segmento por cidade.'
                    )
        
        return cleaned_data


class VideoForm(forms.ModelForm):
    """Formulário para vídeos"""

    class Meta:
        model = Video
        fields = ['titulo', 'descricao', 'arquivo', 'qrcode_url_destino', 'qrcode_descricao', 'texto_tarja']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Título do vídeo'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descrição do vídeo'}),
            'arquivo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'video/*'}),
            'qrcode_url_destino': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://exemplo.com/promoção'
            }),
            'qrcode_descricao': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Resgate seu desconto!'
            }),
            'texto_tarja': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ex: Faça um storie com #media123 e ganhe uma lavagem grátis!',
                'maxlength': '300'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Se estiver editando um vídeo que já tem arquivo, não exige novo upload
        if self.instance and self.instance.pk and self.instance.arquivo:
            self.fields['arquivo'].required = False


class PlaylistForm(forms.ModelForm):
    """Formulário para playlists"""

    class Meta:
        model = Playlist
        fields = ['nome', 'descricao', 'municipio', 'ativa']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome da playlist'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descrição da playlist'}),
            'municipio': forms.Select(attrs={'class': 'form-select'}),
            'ativa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filtrar municípios baseado no usuário
        if user:
            if user.is_franchisee():
                self.fields['municipio'].queryset = Municipio.objects.filter(franqueado=user)
            elif user.is_owner():
                self.fields['municipio'].queryset = Municipio.objects.all()


class DispositivoTVForm(forms.ModelForm):
    """Formulário para dispositivos TV"""

    class Meta:
        model = DispositivoTV
        fields = ['nome', 'localizacao', 'municipio', 'playlist_atual', 'publico_estimado_mes', 'ativo']
        # identificador_unico é gerado automaticamente na view
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do dispositivo'}),
            'localizacao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Localização (ex: Praça Central)'}),
            'municipio': forms.Select(attrs={'class': 'form-select'}),
            'playlist_atual': forms.Select(attrs={'class': 'form-select'}),
            'publico_estimado_mes': forms.NumberInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Ex: 5000',
                'min': '0'
            }),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar apenas playlists ativas
        self.fields['playlist_atual'].queryset = Playlist.objects.filter(ativa=True)


class AgendamentoExibicaoForm(forms.ModelForm):
    """Formulário para agendamento de horários de exibição"""
    
    # Campos para checkboxes dos dias da semana
    segunda = forms.BooleanField(required=False, label='Segunda-feira')
    terca = forms.BooleanField(required=False, label='Terça-feira')
    quarta = forms.BooleanField(required=False, label='Quarta-feira')
    quinta = forms.BooleanField(required=False, label='Quinta-feira')
    sexta = forms.BooleanField(required=False, label='Sexta-feira')
    sabado = forms.BooleanField(required=False, label='Sábado')
    domingo = forms.BooleanField(required=False, label='Domingo')

    class Meta:
        model = AgendamentoExibicao
        fields = ['nome', 'hora_inicio', 'hora_fim', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do agendamento'}),
            'hora_inicio': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'hora_fim': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Se está editando, carregar os dias selecionados
        if self.instance and self.instance.pk and self.instance.dias_semana:
            dias_mapping = {
                0: 'segunda',
                1: 'terca',
                2: 'quarta',
                3: 'quinta',
                4: 'sexta',
                5: 'sabado',
                6: 'domingo'
            }
            for dia_num, dia_nome in dias_mapping.items():
                if dia_num in self.instance.dias_semana:
                    self.fields[dia_nome].initial = True

    def clean(self):
        cleaned_data = super().clean()
        
        # Validar horários
        hora_inicio = cleaned_data.get('hora_inicio')
        hora_fim = cleaned_data.get('hora_fim')
        
        if hora_inicio and hora_fim and hora_inicio >= hora_fim:
            raise forms.ValidationError('A hora de início deve ser anterior à hora de término.')
        
        # Validar dias da semana
        dias_selecionados = []
        dias_mapping = {
            'segunda': 0,
            'terca': 1,
            'quarta': 2,
            'quinta': 3,
            'sexta': 4,
            'sabado': 5,
            'domingo': 6
        }
        
        for dia_nome, dia_num in dias_mapping.items():
            if cleaned_data.get(dia_nome):
                dias_selecionados.append(dia_num)
        
        if not dias_selecionados:
            raise forms.ValidationError('Selecione pelo menos um dia da semana.')
        
        cleaned_data['dias_semana'] = dias_selecionados
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.dias_semana = self.cleaned_data['dias_semana']
        if commit:
            instance.save()
        return instance


class AppVersionForm(forms.ModelForm):
    """Formulário para upload de versões do aplicativo"""
    
    class Meta:
        model = AppVersion
        fields = ['versao', 'arquivo_apk', 'notas_versao', 'ativo']
        widgets = {
            'versao': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Ex: 1.0.0, 1.2.5'
            }),
            'arquivo_apk': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.apk'
            }),
            'notas_versao': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 4, 
                'placeholder': 'Descreva as novidades e correções desta versão...'
            }),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean_arquivo_apk(self):
        arquivo = self.cleaned_data.get('arquivo_apk')
        if arquivo:
            # Verificar extensão
            if not arquivo.name.endswith('.apk'):
                raise forms.ValidationError('O arquivo deve ter a extensão .apk')
            
            # Verificar tamanho (máximo 100MB)
            if arquivo.size > 100 * 1024 * 1024:
                raise forms.ValidationError('O arquivo não pode ter mais de 100 MB')
        
        return arquivo
    
    def clean_versao(self):
        versao = self.cleaned_data.get('versao')
        if versao:
            # Validar formato da versão (apenas números e pontos)
            import re
            if not re.match(r'^\d+(\.\d+){0,2}$', versao):
                raise forms.ValidationError('Formato inválido. Use: X.Y.Z (ex: 1.0.0, 1.2.5)')
        
        return versao


class ConteudoCorporativoForm(forms.ModelForm):
    """Formulário para criar/editar conteúdo corporativo"""

    class Meta:
        model = ConteudoCorporativo
        fields = ['titulo', 'tipo', 'duracao_segundos', 'ativo']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Previsão do Tempo SP'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'duracao_segundos': forms.NumberInput(attrs={'class': 'form-control', 'min': '5', 'max': '120'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ConfiguracaoAPIForm(forms.ModelForm):
    """Formulário para configuração das APIs externas"""

    class Meta:
        model = ConfiguracaoAPI
        fields = [
            'weather_max_requests_dia',
            'cotacoes_max_requests_dia',
            'noticias_api_key',
            'noticias_max_requests_dia',
            'cache_weather_minutos',
            'cache_cotacoes_minutos',
            'cache_noticias_minutos',
        ]
        widgets = {
            'weather_max_requests_dia': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'cotacoes_max_requests_dia': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'noticias_api_key': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Cole sua chave da NewsAPI.org aqui'}),
            'noticias_max_requests_dia': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'cache_weather_minutos': forms.NumberInput(attrs={'class': 'form-control', 'min': '5'}),
            'cache_cotacoes_minutos': forms.NumberInput(attrs={'class': 'form-control', 'min': '5'}),
            'cache_noticias_minutos': forms.NumberInput(attrs={'class': 'form-control', 'min': '5'}),
        }
