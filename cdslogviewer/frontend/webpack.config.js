var webpack = require("webpack");
var path = require("path");
var TerserPlugin = require("terser-webpack-plugin");

var BUILD_DIR = path.resolve(__dirname, "../public/javascripts");
var APP_DIR = path.resolve(__dirname, "app");

var config = {
    entry: `${APP_DIR}/index.jsx`,
    output: {
        path: BUILD_DIR,
        filename: "bundle.js",
    },
    resolve: {
        extensions: [".ts", ".tsx", ".js", ".jsx"],
        fallback: {
            stream: require.resolve("stream-browserify"),
            util: require.resolve("util/"),
            crypto: require.resolve("crypto-browserify"),
            buffer: require.resolve("buffer/")
        },
    },
    optimization: {
        minimizer: [new TerserPlugin()],
    },
    module: {
        rules: [
            {
                enforce: "pre",
                test: /\.js$/,
                exclude: /node_modules/,
                loader: "source-map-loader",
            },
            {
                test: /\.m?js$/,
                resolve: {
                    fullySpecified: false,
                },
                type: "javascript/auto", //see https://github.com/webpack/webpack/issues/11467
            },
            {
                test: /\.[tj]sx?/,
                include: APP_DIR,
                loader: "ts-loader",
            },
            {
                test: /\.(css|s[ac]ss)$/,
                use: ["style-loader", "css-loader", "sass-loader"],
            },
        ],
    },
    devtool: "source-map",
    plugins: [
        new webpack.ProvidePlugin({
            process: "process/browser",
        }),
    ],
};

module.exports = config;
