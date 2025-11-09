// Artillery Scenario Processor
// Custom functions for load testing

module.exports = {
  randomEmail,
  randomSymbol,
  randomQuantity,
  randomOrderType,
  randomTimeframe
};

function randomEmail(context, events, done) {
  const timestamp = Date.now();
  const random = Math.floor(Math.random() * 10000);
  context.vars.email = `trader${timestamp}${random}@example.com`;
  return done();
}

function randomSymbol(context, events, done) {
  const symbols = [
    'RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK',
    'HINDUNILVR', 'ITC', 'SBIN', 'BHARTIARTL', 'KOTAKBANK'
  ];
  context.vars.symbol = symbols[Math.floor(Math.random() * symbols.length)];
  return done();
}

function randomQuantity(context, events, done) {
  const quantities = [1, 5, 10, 25, 50, 100];
  context.vars.quantity = quantities[Math.floor(Math.random() * quantities.length)];
  return done();
}

function randomOrderType(context, events, done) {
  const types = ['market', 'limit'];
  context.vars.orderType = types[Math.floor(Math.random() * types.length)];
  return done();
}

function randomTimeframe(context, events, done) {
  const timeframes = ['1m', '5m', '15m', '1h', '1d'];
  context.vars.timeframe = timeframes[Math.floor(Math.random() * timeframes.length)];
  return done();
}
