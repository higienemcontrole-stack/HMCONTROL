// Dashboard Logic - HM Control Excel Twin Edition
let dashboardCharts = {};

document.addEventListener('DOMContentLoaded', async () => {
    await initDashboard();
});

async function initDashboard(unit = 'TODAS', month = 'TODOS', year = 'TODOS') {
    try {
        const url = `/api/excel/dashboard?unit=${unit}&month=${month}&year=${year}`;
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
            'title-moments-main': 'ADESÃO AOS 5 MOMENTOS DE HIGIENE DE MÃOS',
            'title-moments-stacked': 'ADESÃO POR MOMENTO AUDITADO',
            'title-categories': 'ADESÃO POR CATEGORIA PROFISSIONAL',
            'title-realized-lost': 'OPORTUNIDADES REALIZADAS X PERDIDAS',
            'title-units': 'ADESÃO POR UNIDADE'
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
    const defaultColors = { sim: '#ED7D31', nao: '#4472C4' }; // Padrão Excel (Novo)
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
    const isComparison = currentYear === 'TODOS';
    
    // Calcular porcentagens para as barras (Fidelidade Excel)
    const sims = items.map(i => showMeta ? (i.sim / i.total * 100) : i.sim);
    const naos = items.map(i => showMeta ? (i.nao / i.total * 100) : i.nao);

    const config = {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                { label: 'Não', data: naos, backgroundColor: colors.nao, borderRadius: 2 },
                { label: 'Sim', data: sims, backgroundColor: colors.sim, borderRadius: 2 }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            layout: {
                padding: {
                    bottom: 40
                }
            },
            plugins: {
                legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 10 } } },
                annotation: showMeta ? {
                    annotations: {
                        line1: {
                            type: 'line',
                            yMin: metaValue,
                            yMax: metaValue,
                            borderColor: '#1F3864',
                            borderWidth: 3,
                            label: {
                                display: false
                            }
                        }
                    }
                } : {}
            },
            scales: {
                x: {
                    stacked: isComparison, // Ativa empilhamento apenas no modo comparação
                    ticks: {
                        maxRotation: 45,
                        minRotation: 0,
                        font: { size: 10 }
                    }
                },
                y: { 
                    stacked: isComparison, // Ativa empilhamento apenas no modo comparação
                    beginAtZero: true,
                    max: showMeta ? 100 : undefined,
                    ticks: {
                        callback: function(value) { return value + (showMeta ? '%' : ''); }
                    }
                }
            }
        }
    };

    // Se for gráfico de adesão (porcentagem), ajustamos a escala e a meta
    if (showMeta) {
        // Para bater com o Excel, o ideal é o gráfico mostrar as barras mas as pessoas verem a adesão.
        // No Excel da imagem, as barras são agrupadas SIM/NÃO em valores absolutos, e a linha de meta parece cruzar os eixos.
        // Vamos colocar a linha de meta como uma anotação de "valor" se fosse % , mas aqui são valores absolutos.
        // Vou apenas renderizar as barras conforme a imagem.
    }

    return new Chart(document.getElementById(canvasId), config);
}

// Função para expandir/recolher slicers (Fidelidade UI solicitada)
window.toggleSlicer = function(header) {
    const box = header.parentElement;
    box.classList.toggle('collapsed');
}
