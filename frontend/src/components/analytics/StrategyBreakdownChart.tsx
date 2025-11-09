import { Card, CardContent, Typography, Box } from '@mui/material';
import Plot from 'react-plotly.js';
import type { StrategyPerformance } from '../../types';

interface StrategyBreakdownChartProps {
  data: StrategyPerformance[];
  title?: string;
}

export default function StrategyBreakdownChart({ data, title = 'Strategy Performance Comparison' }: StrategyBreakdownChartProps) {
  const strategyNames = data.map(s => s.strategyName);
  const returns = data.map(s => s.totalReturn * 100);
  const colors = returns.map(r => r >= 0 ? '#2e7d32' : '#d32f2f');

  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          {title}
        </Typography>
        <Box sx={{ width: '100%', height: 400 }}>
          <Plot
            data={[
              {
                x: strategyNames,
                y: returns,
                type: 'bar',
                marker: {
                  color: colors,
                },
                text: returns.map(r => `${r.toFixed(2)}%`),
                textposition: 'outside',
                hovertemplate: '<b>%{x}</b><br>Return: %{y:.2f}%<extra></extra>',
              } as any,
            ]}
            layout={{
              autosize: true,
              margin: { l: 60, r: 30, t: 30, b: 100 },
              xaxis: {
                title: { text: 'Strategy' },
                tickangle: -45,
              },
              yaxis: {
                title: { text: 'Total Return (%)' },
                tickformat: '.2f',
              },
              showlegend: false,
            }}
            config={{
              responsive: true,
              displayModeBar: false,
            }}
            style={{ width: '100%', height: '100%' }}
          />
        </Box>
      </CardContent>
    </Card>
  );
}
