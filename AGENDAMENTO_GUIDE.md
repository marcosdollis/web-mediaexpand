# Sistema de Agendamento de Exibição

## Visão Geral

O sistema de agendamento permite configurar horários específicos para exibição de conteúdo nos dispositivos de TV. Fora dos horários agendados, a TV exibirá uma tela preta (como se estivesse desligada).

## Conceitos Principais

### Agendamento de Exibição
- **Nome**: Identificação descritiva do agendamento (ex: "Horário Comercial", "Final de Semana")
- **Dias da Semana**: Quais dias o agendamento está ativo (Segunda a Domingo)
- **Horário**: Hora de início e fim da exibição
- **Status**: Ativo/Inativo (para desabilitar temporariamente sem deletar)

### Comportamento do Sistema

#### Sem Agendamentos
- Se um dispositivo **não tem agendamentos** ou **não tem agendamentos ativos**, ele exibirá conteúdo **24 horas por dia, 7 dias por semana**.

#### Com Agendamentos
- Se um dispositivo tem **um ou mais agendamentos ativos**, ele exibirá conteúdo **APENAS** nos horários e dias configurados.
- Fora dos horários agendados, a TV mostrará uma **tela preta**.
- Se existe **mais de um agendamento ativo**, a exibição acontece se **qualquer um** deles permitir (união dos horários).

## Como Usar

### Criar Agendamento

1. Acesse a página de detalhes do dispositivo
2. Na seção "Agendamentos de Exibição", clique em "Novo Agendamento"
3. Preencha o formulário:
   - **Nome**: Ex: "Horário Comercial"
   - **Dias da Semana**: Selecione os dias (ex: Seg-Sex para dias úteis)
   - **Hora de Início**: Ex: 08:00
   - **Hora de Término**: Ex: 18:00
   - **Ativo**: Mantenha marcado para ativar imediatamente
4. Clique em "Criar Agendamento"

### Editar Agendamento

1. Na página de detalhes do dispositivo, encontre o agendamento
2. Clique no botão de editar (ícone de lápis)
3. Modifique os campos necessários
4. Clique em "Salvar Alterações"

### Deletar Agendamento

1. Na página de detalhes do dispositivo, encontre o agendamento
2. Clique no botão de deletar (ícone de lixeira)
3. Confirme a exclusão

### Desativar Temporariamente

Para parar um agendamento sem deletá-lo:
1. Edite o agendamento
2. Desmarque a opção "Agendamento Ativo"
3. Salve as alterações

## Exemplos de Uso

### Exemplo 1: Loja Comercial
**Necessidade**: Exibir conteúdo apenas no horário de funcionamento

**Configuração**:
- Nome: "Horário de Funcionamento"
- Dias: Segunda a Sábado
- Horário: 09:00 às 19:00
- Resultado: TV exibe conteúdo de 9h às 19h em dias úteis e sábados. Domingo e madrugadas: tela preta.

### Exemplo 2: Shopping com Horários Diferentes
**Necessidade**: Horários diferentes para dias úteis e finais de semana

**Configuração 1**:
- Nome: "Dias Úteis"
- Dias: Segunda a Sexta
- Horário: 10:00 às 22:00

**Configuração 2**:
- Nome: "Final de Semana"
- Dias: Sábado e Domingo
- Horário: 10:00 às 23:00

**Resultado**: TV exibe de 10h-22h em dias úteis e 10h-23h nos finais de semana.

### Exemplo 3: Evento Especial
**Necessidade**: Exibição contínua durante um evento de 3 dias

**Configuração**:
- Criar agendamento para o evento cobrindo todo o período
- Após o evento, desativar ou deletar o agendamento
- Voltar aos agendamentos normais

### Exemplo 4: Exibição 24/7
**Necessidade**: TV sempre ligada exibindo conteúdo

**Configuração**:
- **Não criar nenhum agendamento** OU
- **Desativar todos os agendamentos existentes**

**Resultado**: TV exibe conteúdo 24 horas por dia.

## API para Aplicativo Android TV

### Endpoint: Verificar Horário de Exibição

**URL**: `GET /api/tv/check-schedule/{identificador_unico}/`

**Resposta com Agendamentos**:
```json
{
  "should_display": true,
  "current_time": "2024-01-15T14:30:00-03:00",
  "dispositivo_nome": "TV Praça Central",
  "has_playlist": true,
  "playlist_id": 5,
  "playlist_nome": "Playlist Principal",
  "agendamentos": [
    {
      "nome": "Horário Comercial",
      "dias_semana": [0, 1, 2, 3, 4],
      "hora_inicio": "08:00",
      "hora_fim": "18:00"
    }
  ]
}
```

**Resposta Sem Agendamentos (24/7)**:
```json
{
  "should_display": true,
  "current_time": "2024-01-15T14:30:00-03:00",
  "dispositivo_nome": "TV Praça Central",
  "has_playlist": true,
  "playlist_id": 5,
  "playlist_nome": "Playlist Principal",
  "agendamentos": [],
  "message": "Sem agendamentos: exibição 24/7"
}
```

**Resposta Fora do Horário**:
```json
{
  "should_display": false,
  "current_time": "2024-01-15T22:30:00-03:00",
  "dispositivo_nome": "TV Praça Central",
  "has_playlist": true,
  "agendamentos": [
    {
      "nome": "Horário Comercial",
      "dias_semana": [0, 1, 2, 3, 4],
      "hora_inicio": "08:00",
      "hora_fim": "18:00"
    }
  ]
}
```

### Lógica no App Android

```kotlin
// Verificar a cada X minutos (ex: 5 minutos)
fun checkSchedule() {
    val response = api.checkSchedule(deviceUUID)
    
    if (response.shouldDisplay) {
        // Exibir conteúdo normalmente
        if (response.hasPlaylist) {
            playPlaylist(response.playlistId)
        }
    } else {
        // Exibir tela preta
        showBlackScreen()
    }
}

// Implementação da tela preta
fun showBlackScreen() {
    setContentView(View(this).apply {
        setBackgroundColor(Color.BLACK)
        keepScreenOn = true
    })
}
```

## Considerações Importantes

### Fuso Horário
- Todos os horários são interpretados no **fuso horário do servidor**
- O app Android recebe o `current_time` no formato ISO 8601 com timezone

### Sincronização
- Recomenda-se que o app verifique o agendamento a cada **5 minutos**
- Durante transições (entrada/saída do horário), o app deve verificar com mais frequência
- O endpoint atualiza automaticamente o campo `ultima_sincronizacao` do dispositivo

### Múltiplos Agendamentos
- Quando há **múltiplos agendamentos ativos**, a TV exibe conteúdo se **QUALQUER UM** permitir
- Exemplo: Se um agendamento permite 8h-12h e outro 14h-18h, a TV exibe nesses dois períodos

### Desempenho
- Agendamentos inativos são **ignorados** na verificação
- A verificação é **otimizada** e não impacta performance

## Permissões

### Owner (Proprietário)
- Pode criar, editar e deletar agendamentos de **qualquer dispositivo**

### Franchisee (Franqueado)
- Pode criar, editar e deletar agendamentos de dispositivos dos **seus municípios**

### Client (Cliente)
- **Não tem acesso** ao gerenciamento de agendamentos

## Admin Django

Os agendamentos também podem ser gerenciados pelo admin do Django:
- URL: `/admin/core/agendamentoexibicao/`
- Filtros disponíveis: Status (Ativo/Inativo), Município do dispositivo
- Visualização em lista com dias da semana e horários

## Troubleshooting

### TV não exibe conteúdo no horário esperado
1. Verifique se o agendamento está **ativo**
2. Confirme os **dias da semana** selecionados
3. Confirme os **horários** (início deve ser antes do término)
4. Verifique o **fuso horário** do servidor
5. Confirme que o **dispositivo está ativo**
6. Verifique se há uma **playlist associada** ao dispositivo

### TV exibe conteúdo quando deveria estar com tela preta
1. Verifique se existem **outros agendamentos ativos** não esperados
2. Confirme o **horário atual** do servidor
3. Verifique se o app está **verificando o agendamento regularmente**

### Tela preta 24 horas
1. Verifique se existe **pelo menos um agendamento ativo**
2. Confirme que os **horários cobrem o período desejado**
3. Verifique se o **dispositivo está ativo**

## Migração e Banco de Dados

### Modelo AgendamentoExibicao
```python
class AgendamentoExibicao(models.Model):
    dispositivo = ForeignKey(DispositivoTV)
    nome = CharField(max_length=200)
    dias_semana = JSONField(default=list)  # [0,1,2,3,4] = Seg-Sex
    hora_inicio = TimeField()
    hora_fim = TimeField()
    ativo = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

### Campo dias_semana
- Armazenado como **JSON array**
- Valores: 0 = Segunda, 1 = Terça, ..., 6 = Domingo
- Exemplo: `[0, 1, 2, 3, 4]` = Segunda a Sexta
- Exemplo: `[5, 6]` = Sábado e Domingo

## Recursos Relacionados

- [API_TV_GUIDE.md](./API_TV_GUIDE.md) - Guia completo da API para Android TV
- [ESTRUTURA.md](./ESTRUTURA.md) - Estrutura do projeto
- [RESUMO_EXECUTIVO.md](./RESUMO_EXECUTIVO.md) - Visão geral do sistema
