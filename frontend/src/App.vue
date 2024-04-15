<template>
    <nav>
        <router-link to="/">Home</router-link> |
        <router-link to="/about">About</router-link>
    </nav>
    <router-view />
    <h2>{{ name }}</h2>
    <div><button v-on:click="changeName">Change name</button></div>
    <h2>{{ count }}</h2>
    <div><button v-on:click="increment(5, $event)">Increment</button></div>
    <div><button v-on:click="decrement(5)">Decrement</button></div>
    <div>
        <button @mouseover="increment(1)">Mouseover increment</button>
    </div>
</template>

<script>
    export default {
        name: 'App',
        data() {
            return {
                name: 'Name',
                count: 0,
            };
        },
        methods: {
            changeName(event) {
                this.name = 'Batman';
                console.log(event);
            },
            increment(num, event) {
                this.count += num;
                console.log(event);
            },
            decrement(num) {
                this.count -= num;
            },
        },
    };
</script>

<style>
    #app {
        font-family: Avenir, Helvetica, Arial, sans-serif;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
        text-align: center;
        color: #2c3e50;
    }

    nav {
        padding: 30px;
    }

    nav a {
        font-weight: bold;
        color: #2c3e50;
    }

    nav a.router-link-exact-active {
        color: #42b983;
    }
</style>
