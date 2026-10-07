//(a)Basic arithmetic opertaions
let a = 25 , b = 8;
console.log("Sum of",a,"and",b,":",a+b);
console.log("Difference of",a,"and",b,":",a-b);
console.log("Product of",a,"and",b,":",a*b);
console.log("Division of",a,"by",b,":",a/b);
console.log("Remainder of",a,"divided by",b,":",a%b);
alert("Sum : "+(a+b));




//(b)Array operations on dynamic price list
let prices = [45,120,30,250,80];
console.log("Original price list :",prices);
prices.push(99);//insertion
console.log("After inserting 99 :",prices);

let pos = prices.indexOf(30);//searching
if (pos !== -1) 
    prices.splice(pos,1);//deletion
    console.log("After deleting 30:",prices);

console.log("Search 250 found at index:",prices.indexOf(250));//searching
prices.sort((x,y)=>x-y);//numerical sorting
console.log("Sorted (ascending) :",prices);

//Supermarket billing with bulk discount
let cart = [
    {item:"Rice", price:60, qty:2},
    {item:"Oil", price:110, qty:12},
    {item:"Sugar", price:42, qty:5}
];
let subtotal=0,bulk=false;
for(let c of cart){
    subtotal += c.price * c.qty;
    if(c.qty>10) bulk=true;//bulk purchase rule
}
let discount=bulk?0.1*subtotal:0;
let total=subtotal-discount;
console.log("Subtotal:Rs.",subtotal.toFixed(2));
console.log("Bulk Discount(10%):",discount.toFixed(2));
console.log("Final payable amount:Rs.",total.toFixed(2));
alert("Final payable amount :Rs."+total.toFixed(2));