module.exports = {
  sourceDir: __dirname,
  artifactsDir: `${__dirname}/dist`,
  ignoreFiles: ["package.json", "package-lock.json", "node_modules", ".web-extrc.js", "dist"],
  build: { overwriteDest: true },
  run: { startUrl: ["about:debugging#/runtime/this-firefox"] },
};
