from django import forms
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import User, Municipio, Cliente, Video, Playlist, DispositivoTV, AgendamentoExibicao


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
        fields = ['nome', 'estado', 'franqueado']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do município'}),
            'estado': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Estado (UF)'}),
            'franqueado': forms.Select(attrs={'class': 'form-select'}),
        }


class ClienteForm(forms.ModelForm):
    """Formulário para clientes"""

    class Meta:
        model = Cliente
        fields = ['user', 'empresa', 'municipios', 'franqueado', 'ativo', 'observacoes']
        widgets = {
            'user': forms.Select(attrs={'class': 'form-select'}),
            'empresa': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome da empresa'}),
            'municipios': forms.SelectMultiple(attrs={'class': 'form-select'}),
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


class VideoForm(forms.ModelForm):
    """Formulário para vídeos"""

    class Meta:
        model = Video
        fields = ['titulo', 'descricao', 'arquivo']
        widgets = {
            'titulo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Título do vídeo'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descrição do vídeo'}),
            'arquivo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'video/*'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remover o campo cliente se não for necessário (é definido automaticamente)


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
        fields = ['nome', 'localizacao', 'municipio', 'playlist_atual', 'ativo']
        # identificador_unico é gerado automaticamente na view
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do dispositivo'}),
            'localizacao': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Localização (ex: Praça Central)'}),
            'municipio': forms.Select(attrs={'class': 'form-select'}),
            'playlist_atual': forms.Select(attrs={'class': 'form-select'}),
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
