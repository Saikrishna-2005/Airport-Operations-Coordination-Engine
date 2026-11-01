const fs = require("fs");
const path = require("path");
const postcss = require("postcss");
const selectorParser = require("postcss-selector-parser");

// Original CSS from your friend's Weather project
const cssPath = path.join(
  __dirname,
  "../src/pages/Weather.css"
);

// Generated CSS scoped to the Weather module
const outputPath = path.join(
  __dirname,
  "../src/pages/Weather.scoped.css"
);

const css = fs.readFileSync(cssPath, "utf8");
const root = postcss.parse(css);

// Process every CSS rule
root.walkRules((rule) => {
  // Skip selectors inside keyframe animations
  let parent = rule.parent;

  while (parent) {
    if (
      parent.type === "atrule" &&
      /keyframes$/i.test(parent.name)
    ) {
      return;
    }

    parent = parent.parent;
  }

  // Prefix selectors with .weather-module
  rule.selector = selectorParser((selectors) => {
    selectors.each((selector) => {
      // Remove formatting-only whitespace before the first node.
      const first = selector.nodes.find(
        (node) =>
          node.type !== "comment" &&
          node.type !== "combinator"
      );

      if (!first) return;

      // Replace global html and body selectors.
      if (
        first.type === "tag" &&
        ["html", "body"].includes(first.value.toLowerCase())
      ) {
        first.replaceWith(
          selectorParser.className({
            value: "weather-module",
          })
        );

        return;
      }

      // Replace :root with .weather-module.
      if (
        first.type === "pseudo" &&
        first.value.toLowerCase() === ":root"
      ) {
        first.replaceWith(
          selectorParser.className({
            value: "weather-module",
          })
        );

        return;
      }

      // Avoid adding the prefix twice.
      if (
        first.type === "class" &&
        first.value === "weather-module"
      ) {
        return;
      }

      // Add the wrapper to each selector separately.
      selector.prepend(
        selectorParser.combinator({
          value: " ",
        })
      );

      selector.prepend(
        selectorParser.className({
          value: "weather-module",
        })
      );
    });
  }).processSync(rule.selector, {
    lossless: false,
  });
});

// Write the generated CSS without modifying the original.
fs.writeFileSync(
  outputPath,
  root.toString(),
  "utf8"
);

console.log("Weather CSS scoped successfully!");
console.log("Output:", outputPath);