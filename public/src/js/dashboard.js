// Dashboard Logic - HM Control Dados Twin Edition
let dashboardCharts = {};

document.addEventListener('DOMContentLoaded', async () => {
    await initDashboard();
});

async function initDashboard(unit = 'TODAS', month = 'TODOS', year = 'TODOS') {
    try {
        const url = `/api/data/dashboard?unit=${unit}&month=${month}&year=${year}`;
        const res = await fetch(url);
        const data = await res.json();

        // --- Atualização Global de Títulos Dinâmicos (Clareza Total) ---
        let yearSuffix = '';
        if (year === 'TODOS') {
            const availableYears = data.filters.years.map(y => parseInt(y)).sort((a, b) => a - b);
            if (availableYears.length > 1) {
                yearSuffix = ` - PERÍODO TOTAL (${availableYears[0]} a ${availableYears[availableYears.length - 1]})`;
            } else {
                yearSuffix = ` - PERÍODO TOTAL`;
            }
        } else {
            yearSuffix = ` - ${year}`;
        }

        // Mapeamento de Títulos Originais + Sufixo do Ano
        const titleMappings = {
            'title-moments-main': 'MONITORAMENTO DOS 5 MOMENTOS',
            'title-moments-stacked': 'QUANTIDADE POR MOMENTO AUDITADO',
            'title-categories': 'MONITORAMENTO POR CATEGORIA PROFISSIONAL',
            'title-realized-lost': 'VOLUME DE MONITORAMENTOS MENSAL',
            'title-units': 'MONITORAMENTO POR UNIDADE'
        };

        // Aplicar a todos os elementos encontrados
        Object.entries(titleMappings).forEach(([id, baseText]) => {
            const el = document.getElementById(id);
            if (el) el.textContent = `${baseText}${yearSuffix}`;
        });

        if (dashboardCharts.momentsMain) {
            // Se já existem gráficos, destrói para recriar
            Object.values(dashboardCharts).forEach(chart => chart.destroy());
        }

        renderSlicers(data.filters, unit, month, year);
        renderCharts(data, year);

    } catch (err) {
        console.error('Erro ao inicializar dashboard:', err);
    }
}

function renderSlicers(filters, currentUnit, currentMonth, currentYear) {
    const unitList = document.getElementById('slicer-unit');
    const monthList = document.getElementById('slicer-month');
    const yearList = document.getElementById('slicer-year');

    // Manter o "TODAS/TODOS" e injetar o resto
    updateSlicerUI(unitList, filters.units, currentUnit, 'TODAS', (val) => initDashboard(val, currentMonth, currentYear));
    updateSlicerUI(monthList, filters.months, currentMonth, 'TODOS', (val) => initDashboard(currentUnit, val, currentYear));
    updateSlicerUI(yearList, filters.years, currentYear, 'TODOS', (val) => initDashboard(currentUnit, currentMonth, val));
}

function updateSlicerUI(container, items, currentVal, defaultLabel, onSelect) {
    container.innerHTML = ''; // Limpa o container para reconstrução limpa
    
    // 1. Criar o item padrão (ex: TODOS) com evento funcional
    const defaultLi = document.createElement('li');
    defaultLi.className = `slicer-item ${currentVal === defaultLabel ? 'active' : ''}`;
    defaultLi.textContent = defaultLabel;
    defaultLi.dataset.value = defaultLabel;
    defaultLi.onclick = () => onSelect(defaultLabel);
    container.appendChild(defaultLi);
    
    // 2. Criar os demais itens dinâmicos do banco de dados
    items.forEach(item => {
        const li = document.createElement('li');
        // Normalização de string para comparação de estados ativos (evita erro de tipo int vs string)
        li.className = `slicer-item ${String(currentVal) === String(item) ? 'active' : ''}`;
        li.textContent = item;
        li.dataset.value = item;
        li.onclick = () => onSelect(item);
        container.appendChild(li);
    });
}

function renderCharts(data, currentYear) {
    const defaultColors = { sim: '#ED7D31', nao: '#4472C4' }; // Padrão Dados (Novo)
    const momentsColors = { sim: '#FFC000', nao: '#ED7D31' }; // Específico do 1º gráfico da imagem

    // 1. Gráfico Principal (Top Large) - Adesão 5 Momentos
    dashboardCharts.momentsMain = createGroupedBar('chart-moments-main', data.moments, momentsColors, true, 80, currentYear);

    // 2. Adesão por Momento (Stacked/Grouped)
    dashboardCharts.momentsStacked = createGroupedBar('chart-moments-stacked', data.moments, defaultColors, true, 85, currentYear);

    // 3. Adesão por Categoria
    dashboardCharts.categories = createGroupedBar('chart-categories', data.categories, defaultColors, true, 85, currentYear);

    // 4. Oportunidades Realizadas x Perdidas
    dashboardCharts.realizedLost = createGroupedBar('chart-realized-lost', data.timeline, defaultColors, false, 0, currentYear);

    // 5. Adesão por Unidade
    dashboardCharts.units = createGroupedBar('chart-units', data.units, defaultColors, true, 85, currentYear);
}

function createGroupedBar(canvasId, items, colors, showMeta, metaValue = 85, currentYear = 'TODOS') {
    const labels = items.map(i => i.label);
    const values = items.map(i => i.total);

    const config = {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                { 
                    label: 'Quantidade', 
                    data: values, 
                    backgroundColor: '#3B82F6', 
                    borderRadius: 4,
                    borderWidth: 0
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `Total: ${context.parsed.y} monitoramentos`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    ticks: {
                        maxRotation: 45,
                        minRotation: 0,
                        autoSkip: true,
                        font: { size: 10 }
                    }
                },
                y: { 
                    beginAtZero: true,
                    ticks: {
                        font: { size: 10 },
                        precision: 0
                    }
                }
            }
        }
    };

    // Se for gráfico de adesão (porcentagem), ajustamos a escala e a meta
    if (showMeta) {
        // Para bater com o Dados, o ideal é o gráfico mostrar as barras mas as pessoas verem a adesão.
        // No Dados da imagem, as barras são agrupadas SIM/NÃO em valores absolutos, e a linha de meta parece cruzar os eixos.
        // Vamos colocar a linha de meta como uma anotação de "valor" se fosse % , mas aqui são valores absolutos.
        // Vou apenas renderizar as barras conforme a imagem.
    }

    return new Chart(document.getElementById(canvasId), config);
}

// Função para expandir/recolher slicers (Fidelidade UI e Reconhecimento da Janela)
window.toggleSlicer = function(header) {
    const box = header.parentElement;
    const isCollapsed = box.classList.toggle('collapsed');
    
    // Alternar ícone para feedback visual claro de "reconhecimento"
    const icon = header.querySelector('.toggle-icon');
    if (icon) {
        if (isCollapsed) {
            icon.classList.remove('fa-chevron-down');
            icon.classList.add('fa-chevron-up');
        } else {
            icon.classList.remove('fa-chevron-up');
            icon.classList.add('fa-chevron-up'); // Correção: para baixo é o padrão
            // Na verdade, no print do usuário: Seta para CIMA = Expandido ou Fechado?
            // "os dois campo circulados em vermelho quando preciono a seta para cima a janela não reconhe"
            // Se ele pressiona a seta para cima e não reconhece, significa que ele quer que feche.
            // Logo, fechar = seta para cima. Abrir = seta para baixo.
            icon.classList.remove('fa-chevron-down');
            icon.classList.add('fa-chevron-up');
        }
    }
}

// Re-implementação simplificada para lógica robusta de troca de ícones
window.toggleSlicer = function(header) {
    const box = header.parentElement;
    box.classList.toggle('collapsed');
    
    const icon = header.querySelector('.toggle-icon');
    if (icon) {
        if (box.classList.contains('collapsed')) {
            icon.className = 'fas fa-chevron-up toggle-icon'; // Feedback de fechado
        } else {
            icon.className = 'fas fa-chevron-down toggle-icon'; // Feedback de aberto
        }
    }
}
